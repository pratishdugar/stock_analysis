"""Portfolio UI (Streamlit): holdings, mutual funds + SIPs, other assets, settings, backup."""
import json
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src import backup, market_data as md, mutual_funds as mf, portfolio as pf, settings as settings_mod, storage


@st.cache_data(ttl=3600, show_spinner=False)
def _nav(code, source):
    r = mf.fetch_nav(code, source)
    if not r.ok:
        raise RuntimeError(r.error)
    return r.data


@st.cache_data(ttl=3600, show_spinner=False)
def _usd_inr():
    r = md.fetch_history("INR=X", period="1mo")
    return float(r.data["Close"].iloc[-1]) if r.ok else None


def _money(v, ccy=""):
    return "n/a" if v is None else f"{ccy} {v:,.0f}".strip()


def _pct(v):
    return "n/a" if v is None else f"{v:.1%}"


def _all_data():
    return {t: storage.list_rows(t) for t in storage.TABLES}


def _delete_ui(table, rows, label_fn, key):
    if not rows:
        return
    opts = {label_fn(r): r["id"] for r in rows}
    c1, c2 = st.columns([3, 1])
    pick = c1.selectbox("Select an entry to delete", list(opts), key=f"{key}_pick")
    if c2.button("Delete", key=f"{key}_del"):
        storage.delete_row(table, opts[pick])
        st.rerun()


def portfolio_page(load_history, summarize_symbol):
    cfg = settings_mod.load()
    st.subheader("My Portfolio")
    st.caption("Stored only on this computer (git-ignored `data/` folder). Research aid, not financial advice: "
               "recommendations ignore your tax situation and personal circumstances.")
    if cfg["horizon_years"] < 5:
        st.warning("Your horizon is under 5 years; this app is designed for long-term (5y+) investing.")
    tabs = st.tabs(["Overview & decisions", "Stocks", "Mutual funds & SIPs", "Gold, FDs & other", "Settings", "Backup"])

    with tabs[1]:
        _stocks_tab()
    with tabs[2]:
        _funds_tab()
    with tabs[3]:
        _assets_tab()
    with tabs[4]:
        _settings_tab(cfg)
    with tabs[5]:
        _backup_tab()
    with tabs[0]:
        _overview_tab(cfg, load_history, summarize_symbol)


def _bench_close(load_history, sym):
    h, _ = load_history(sym)
    return h["Close"] if h is not None else None


def _overview_tab(cfg, load_history, summarize_symbol):
    data = _all_data()
    if not any(data[t] for t in ("stock_lots", "funds", "assets")):
        st.info("Nothing here yet. Add holdings in the other tabs, then come back for totals, P&L and decisions.")
        return
    rate = cfg["usd_inr_override"] or None
    with st.spinner("Fetching prices and NAVs (cached for 1h)..."):
        if rate is None:
            rate = _usd_inr()
        fx = {"summary": summarize_symbol, "nav": lambda f: _nav(f["code"], f["source"]),
              "bench": lambda s: _bench_close(load_history, s), "usd_inr": rate}
        r = pf.analyze_portfolio(cfg, data, fx)
    base = r["base"]
    if rate:
        st.caption(f"Totals in {base}. USD/INR used: {rate:.2f}" + (" (manual override)" if cfg["usd_inr_override"] else " (Yahoo)"))
    for w in r["warnings"]:
        st.warning(w)
    for k, v in r["errors"].items():
        st.error(f"{k}: {v}")

    conv = [i for i in r["items"] if "value_base" in i]
    known = [i for i in conv if i["invested_base"] is not None]
    inv = sum(i["invested_base"] for i in known)
    val_known = sum(i["value_base"] for i in known)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Net worth ({base})", _money(r["total"]))
    c2.metric("Invested (where known)", _money(inv))
    c3.metric("Unrealised P&L", _money(val_known - inv), _pct(val_known / inv - 1) if inv else None)
    c4.metric("Active SIPs / month", _money(r["sip_monthly"]))

    _holdings_tables(r)

    st.markdown("#### Allocation vs target")
    alloc = pd.DataFrame(r["allocation"])
    if r["total"]:
        st.plotly_chart(px.pie(alloc[alloc["Value"] > 0], names="Class", values="Value", hole=0.45).update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=0)), width="stretch")
    st.dataframe(alloc, hide_index=True)

    st.markdown("#### Decisions (long-term, rule-based)")
    rows = []
    for s in r["stocks"]:
        rows.append({"Holding": s["symbol"], "Type": "Stock", "Weight %": None if s["weight_pct"] is None else round(s["weight_pct"], 1),
                     "P&L %": _pct(s["pnl_pct"]), "Score": s["rec"]["score"], "Recommendation": s["rec"]["action"],
                     "Why": "; ".join(s["rec"]["reasons"])})
    for f in r["funds"]:
        a = f["analysis"]
        rows.append({"Holding": f["name"], "Type": "Mutual fund", "Weight %": None, "P&L %": _pct(f["pnl_pct"]),
                     "Score": a["score"], "Recommendation": a["rec"], "Why": "; ".join(a["reasons"] + a["risks"])})
    for a in r["assets"]:
        rows.append({"Holding": a["name"], "Type": a["kind"], "Weight %": None, "P&L %": _pct(a["pnl"] / a["invested"]) if a["pnl"] is not None and a["invested"] else "n/a",
                     "Score": None, "Recommendation": a["rec"]["action"], "Why": "; ".join(a["rec"]["reasons"])})
    for a in r["allocation"]:
        if not a["Note"].startswith("Within"):
            rows.append({"Holding": a["Class"], "Type": "Allocation", "Weight %": a["Actual %"], "P&L %": "", "Score": None,
                         "Recommendation": a["Note"], "Why": f"{a['Actual %']}% vs target {a['Target %']}%"})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("A low score means *review*, never an automatic sell. Your purchase price is deliberately ignored in "
               "recommendations (sunk cost). Unofficial data; dividends, tax and exit loads are not modelled.")


def _num(v, nd=2):
    return None if v is None else round(v, nd)


def _holdings_tables(r):
    """Per-holding value, P&L and XIRR in each holding's own currency."""
    if r["stocks"]:
        st.markdown("#### Stocks")
        st.dataframe(pd.DataFrame([{
            "Symbol": s["symbol"], "Currency": s["currency"], "Qty": s["qty"], "Avg cost": _num(s["avg_cost"]),
            "Price": _num(s["price"]), "Invested": _num(s["invested"], 0), "Value": _num(s["value"], 0),
            "P&L": _num(s["pnl"], 0), "P&L %": _pct(s["pnl_pct"]), "XIRR": _pct(s["xirr"]),
            "Weight %": _num(s["weight_pct"], 1)} for s in r["stocks"]]), hide_index=True)
    if r["funds"]:
        st.markdown("#### Mutual funds")
        st.dataframe(pd.DataFrame([{
            "Fund": f["name"], "Category": f["category"], "Currency": f["currency"], "Units": _num(f["units"], 3),
            "Invested": _num(f["invested"], 0), "Value": _num(f["value"], 0), "P&L": _num(f["pnl"], 0),
            "P&L %": _pct(f["pnl_pct"]), "XIRR": _pct(f["xirr"]), "Score": f["analysis"]["score"],
            "CAGR (window)": _pct(f["analysis"]["cagr"]), "Benchmark CAGR": _pct(f["analysis"]["bench_cagr"])}
            for f in r["funds"]]), hide_index=True)
    if r["sips"]:
        st.markdown("#### My SIPs")
        st.dataframe(pd.DataFrame([{
            "Fund": s["fund"], "Monthly amount": s["amount"], "Day": s["day"], "Start": s["start"],
            "End": s["end"] or "-", "Status": "Active" if s["active"] else "Ended", "Invested": _num(s["invested"], 0),
            "Value": _num(s["value"], 0), "Recommendation": s["rec"]} for s in r["sips"]]), hide_index=True)
    if r["assets"]:
        st.markdown("#### Gold, FDs & other")
        st.dataframe(pd.DataFrame([{
            "Type": a["kind"], "Name": a["name"], "Currency": a["currency"], "Invested": _num(a["invested"], 0),
            "Value": _num(a["value"], 0), "Value basis": a["basis"], "P&L": _num(a["pnl"], 0)}
            for a in r["assets"]]), hide_index=True)


def _stocks_tab():
    lots = storage.list_rows("stock_lots")
    with st.form("add_lot", clear_on_submit=True):
        st.markdown("**Add a purchase** (US `AAPL`, NSE `TCS.NS`, BSE `TCS.BO`)")
        c = st.columns(5)
        sym = c[0].text_input("Ticker")
        qty = c[1].number_input("Quantity", min_value=0.0, step=1.0)
        price = c[2].number_input("Buy price (per share)", min_value=0.0, step=0.01)
        bd = c[3].date_input("Buy date", value=date.today())
        ccy = c[4].selectbox("Currency of price", ["INR", "USD"])
        if st.form_submit_button("Add"):
            s, err = md.normalize_symbol(sym)
            if err or qty <= 0 or price <= 0 or bd > date.today():
                st.error(err or "Quantity and price must be > 0 and the date cannot be in the future.")
            else:
                storage.add_row("stock_lots", {"symbol": s, "qty": qty, "price": price, "buy_date": bd.isoformat(), "currency": ccy})
                st.rerun()
    with st.expander("Bulk import from CSV"):
        st.caption("Columns: symbol, qty, price, buy_date (YYYY-MM-DD), currency (INR/USD). One row per purchase.")
        up = st.file_uploader("CSV file", type="csv")
        if up is not None:
            try:
                rows, errs = pf.parse_stock_csv(pd.read_csv(up))
            except Exception as exc:
                rows, errs = [], [f"Could not read CSV ({type(exc).__name__})."]
            for e in errs:
                st.error(e)
            if rows and st.button(f"Import {len(rows)} valid row(s)"):
                for row in rows:
                    storage.add_row("stock_lots", row)
                st.rerun()
    if lots:
        st.dataframe(pd.DataFrame(lots).drop(columns=["notes"]), hide_index=True)
        _delete_ui("stock_lots", lots, lambda r: f"#{r['id']} {r['symbol']} {r['qty']} @ {r['price']} on {r['buy_date']}", "lot")
        st.caption("Current value, P&L, XIRR, weight and recommendation per stock are on the **Overview** tab.")


def _funds_tab():
    funds = storage.list_rows("funds")
    st.markdown("**Add a fund**")
    c = st.columns([3, 1])
    q = c[0].text_input("Search Indian funds by name (uses free mfapi.in)", key="mf_q")
    if c[1].button("Search") and q:
        r = mf.search_funds(q)
        st.session_state["mf_hits"] = r.data if r.ok else []
        if not r.ok:
            st.error(r.error)
    hits = st.session_state.get("mf_hits", [])
    with st.form("add_fund", clear_on_submit=True):
        source = st.selectbox("Source", mf.SOURCES)
        if hits:
            pick = st.selectbox("Search result", [f"{h['code']} - {h['name']}" for h in hits])
        else:
            pick = None
        code = st.text_input("Scheme code / ticker (overrides the search result if filled)")
        name = st.text_input("Display name (optional)")
        c = st.columns(3)
        cat = c[0].selectbox("Category", mf.CATEGORIES)
        bench = c[1].text_input("Benchmark (Yahoo symbol)", value="^NSEI", help="^NSEI Nifty 50, ^GSPC S&P 500; blank = none")
        er = c[2].number_input("Expense ratio % (optional)", min_value=0.0, step=0.05)
        if st.form_submit_button("Add fund"):
            code_f = code.strip() or (pick.split(" - ")[0] if pick else "")
            nm = name.strip() or (pick.split(" - ", 1)[1] if pick and not code.strip() else code_f)
            if not code_f:
                st.error("Enter or pick a scheme code / ticker.")
            else:
                try:
                    _nav(code_f, source)
                except Exception as exc:
                    st.error(f"Could not load that fund: {exc}")
                else:
                    storage.add_row("funds", {"code": code_f, "source": source, "name": nm, "category": cat,
                                              "benchmark": bench.strip() or None, "expense_ratio": er or None,
                                              "currency": "INR" if source.startswith("India") else "USD"})
                    st.rerun()
    if not funds:
        st.info("Add a fund first, then record lump-sum purchases and/or SIPs for it.")
        return
    names = {f"{f['name']} ({f['code']})": f["id"] for f in funds}
    st.dataframe(pd.DataFrame(funds).drop(columns=["id"]), hide_index=True)
    _delete_ui("funds", funds, lambda r: f"#{r['id']} {r['name']}", "fund")
    left, right = st.columns(2)
    with left, st.form("add_flot", clear_on_submit=True):
        st.markdown("**Lump-sum purchase** (don't enter SIP instalments here)")
        fk = st.selectbox("Fund", list(names), key="flot_fund")
        units = st.number_input("Units", min_value=0.0, step=1.0, format="%.3f")
        nav = st.number_input("NAV at purchase", min_value=0.0, step=0.01, format="%.4f")
        bd = st.date_input("Date", value=date.today(), key="flot_date")
        if st.form_submit_button("Add purchase"):
            if units <= 0 or nav <= 0 or bd > date.today():
                st.error("Units and NAV must be > 0 and the date cannot be in the future.")
            else:
                storage.add_row("fund_lots", {"fund_id": names[fk], "units": units, "nav": nav, "buy_date": bd.isoformat()})
                st.rerun()
    with right, st.form("add_sip", clear_on_submit=True):
        st.markdown("**SIP** (units are computed from historical NAVs)")
        fk = st.selectbox("Fund", list(names), key="sip_fund")
        amt = st.number_input("Monthly amount", min_value=0.0, step=500.0)
        day = st.number_input("Day of month", min_value=1, max_value=31, value=5)
        sd = st.date_input("Start date", value=date.today(), key="sip_start")
        has_end = st.checkbox("SIP has ended / has an end date")
        ed = st.date_input("End date", value=date.today(), key="sip_end")
        if st.form_submit_button("Add SIP"):
            if amt <= 0 or (has_end and ed < sd):
                st.error("Amount must be > 0 and the end date cannot precede the start date.")
            else:
                storage.add_row("sips", {"fund_id": names[fk], "amount": amt, "day": int(day), "start_date": sd.isoformat(),
                                         "end_date": ed.isoformat() if has_end else None})
                st.rerun()
    lots = storage.list_rows("fund_lots")
    if lots:
        inv = {v: k for k, v in names.items()}
        st.markdown("**Lump-sum purchases**")
        st.dataframe(pd.DataFrame([{**l, "fund": inv.get(l["fund_id"])} for l in lots]).drop(columns=["fund_id"]), hide_index=True)
        _delete_ui("fund_lots", lots, lambda r: f"#{r['id']} {inv.get(r['fund_id'])} {r['units']} units on {r['buy_date']}", "flot")
    sips = storage.list_rows("sips")
    if sips:
        inv = {v: k for k, v in names.items()}
        st.markdown("**My SIPs** (value and recommendation are on the Overview tab)")
        st.dataframe(pd.DataFrame([{**s, "fund": inv.get(s["fund_id"])} for s in sips]).drop(columns=["fund_id"]), hide_index=True)
        _delete_ui("sips", sips, lambda r: f"#{r['id']} {inv.get(r['fund_id'])} {r['amount']}/month from {r['start_date']}", "sip")
        st.caption("SIP values assume every scheduled instalment succeeded at the NAV on/after the date; "
                   "stamp duty and missed instalments are not modelled.")


def _assets_tab():
    assets = storage.list_rows("assets")
    with st.form("add_asset", clear_on_submit=True):
        st.markdown("**Add gold, FD, PPF/EPF/NPS, private investment, real estate, cash or other**")
        c = st.columns(4)
        kind = c[0].selectbox("Type", pf.ASSET_KINDS)
        name = c[1].text_input("Name")
        ccy = c[2].selectbox("Currency", ["INR", "USD"])
        invested = c[3].number_input("Amount invested", min_value=0.0, step=1000.0)
        c = st.columns(4)
        cur = c[0].number_input("Current value (leave 0 for an FD to auto-estimate)", min_value=0.0, step=1000.0)
        start = c[1].date_input("Start / purchase date", value=date.today())
        rate = c[2].number_input("Interest rate % (FD)", min_value=0.0, step=0.1)
        has_mat = c[3].checkbox("Has maturity date")
        mat = st.date_input("Maturity date", value=date.today(), key="mat")
        qty = st.number_input("Quantity (e.g. grams of gold, optional)", min_value=0.0, step=1.0)
        notes = st.text_input("Notes")
        if st.form_submit_button("Add"):
            if not name.strip() or invested <= 0:
                st.error("Name and amount invested are required.")
            elif kind != "Fixed deposit" and cur <= 0:
                st.error("Enter the current value (your own estimate for private/illiquid assets).")
            elif kind == "Fixed deposit" and cur <= 0 and rate <= 0:
                st.error("For an FD enter an interest rate (value is estimated) or a current value.")
            else:
                storage.add_row("assets", {"kind": kind, "name": name.strip(), "currency": ccy, "invested": invested,
                                           "current_value": cur or None, "start_date": start.isoformat(),
                                           "rate_pct": rate or None, "maturity_date": mat.isoformat() if has_mat else None,
                                           "quantity": qty or None, "updated": date.today().isoformat(), "notes": notes or None})
                st.rerun()
    if assets:
        st.dataframe(pd.DataFrame(assets).drop(columns=["id"]), hide_index=True)
        _delete_ui("assets", assets, lambda r: f"#{r['id']} {r['kind']}: {r['name']}", "asset")
        opts = {f"#{a['id']} {a['name']}": a for a in assets if a["kind"] != "Fixed deposit" or a.get("current_value")}
        if opts:
            with st.form("upd_asset"):
                k = st.selectbox("Update current value of", list(opts))
                nv = st.number_input("New value", min_value=0.0, step=1000.0)
                if st.form_submit_button("Update value") and nv > 0:
                    storage.update_row("assets", opts[k]["id"], {"current_value": nv, "updated": date.today().isoformat()})
                    st.rerun()
    st.caption("Private investments and gold values are your own estimates; update them periodically. "
               "FD values are estimated with quarterly compounding unless you enter a value.")


def _settings_tab(cfg):
    st.markdown("Saved locally; defaults come from `config.py`.")
    with st.form("settings"):
        c = st.columns(3)
        new = dict(cfg)
        new["horizon_years"] = c[0].number_input("Investment horizon (years)", 1, 40, int(cfg["horizon_years"]))
        new["base_currency"] = c[1].selectbox("Base currency", ["INR", "USD"], index=["INR", "USD"].index(cfg["base_currency"]))
        new["usd_inr_override"] = c[2].number_input("USD/INR rate (0 = live from Yahoo)", 0.0, 500.0, float(cfg["usd_inr_override"]))
        c = st.columns(4)
        new["buy_min"] = c[0].number_input("Stock: Buy-more score ≥", 0, 100, int(cfg["buy_min"]))
        new["hold_min"] = c[1].number_input("Stock: Review below score", 0, 100, int(cfg["hold_min"]))
        new["max_position_pct"] = c[2].number_input("Max single stock % of portfolio", 1.0, 100.0, float(cfg["max_position_pct"]))
        new["drift_tolerance_pct"] = c[3].number_input("Allocation drift tolerance (pp)", 0.0, 50.0, float(cfg["drift_tolerance_pct"]))
        c = st.columns(4)
        new["fund_buy_min"] = c[0].number_input("Fund: Continue/add score ≥", 0, 100, int(cfg["fund_buy_min"]))
        new["fund_hold_min"] = c[1].number_input("Fund: Review below score", 0, 100, int(cfg["fund_hold_min"]))
        new["risk_free_pct"] = c[2].number_input("FD-like hurdle return %", 0.0, 30.0, float(cfg["risk_free_pct"]))
        new["inflation_pct"] = c[3].number_input("Assumed inflation %", 0.0, 30.0, float(cfg["inflation_pct"]))
        c = st.columns(2)
        new["fd_alert_days"] = c[0].number_input("Warn FD maturity within (days)", 0, 365, int(cfg["fd_alert_days"]))
        new["stale_value_days"] = c[1].number_input("Warn if manual value older than (days)", 30, 3650, int(cfg["stale_value_days"]))
        st.markdown("**Target allocation (%, must total 100)**")
        cols = st.columns(len(pf.CLASSES))
        new["target_allocation"] = {k: cols[i].number_input(k, 0.0, 100.0, float(cfg["target_allocation"][k]), key=f"t_{k}")
                                    for i, k in enumerate(pf.CLASSES)}
        if st.form_submit_button("Save settings"):
            errs = settings_mod.save(new)
            for e in errs:
                st.error(e)
            if not errs:
                st.success("Saved.")
                st.rerun()


def _backup_tab():
    st.markdown("Your data lives only in `data/stock_research.db` on this computer. Download a backup now and then "
                "(holdings, SIPs, other assets, watchlist and settings).")
    st.download_button("Download backup (JSON)", backup.export_all(), file_name=f"portfolio_backup_{date.today()}.json",
                       mime="application/json")
    up = st.file_uploader("Restore from backup (adds rows; does not delete existing ones)", type="json")
    if up is not None and st.button("Restore"):
        try:
            counts = backup.import_all(json.load(up))
        except Exception as exc:  # invalid file or a value SQLite cannot store: the transaction is rolled back
            st.error(f"Nothing was restored: {exc}")
        else:
            st.success("Restored: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
