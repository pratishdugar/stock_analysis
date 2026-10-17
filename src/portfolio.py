"""Portfolio valuation and rule-based, explainable recommendations. Pure logic: data fetchers are injected.

Recommendations ignore your purchase price (sunk cost) and use the configured long-term horizon.
They do not consider tax, exit loads, or your personal circumstances; they are prompts for review.
"""
from datetime import date

from src import finance, mutual_funds

CLASSES = ["Stocks", "Mutual funds", "Gold", "Fixed deposits", "Private / other"]
ASSET_KINDS = ["Gold", "Fixed deposit", "PPF / EPF / NPS", "Private investment", "Real estate", "Cash / savings", "Other"]
KIND_TO_CLASS = {"Gold": "Gold", "Fixed deposit": "Fixed deposits"}


def d(v):
    return v if isinstance(v, date) else date.fromisoformat(v) if v else None


# ---------- stocks ----------
def aggregate_lots(lots: list[dict]) -> dict:
    out = {}
    for l in lots:
        p = out.setdefault(l["symbol"], {"symbol": l["symbol"], "qty": 0.0, "invested": 0.0, "currency": l.get("currency"),
                                         "flows": [], "first_date": d(l["buy_date"])})
        p["qty"] += l["qty"]
        p["invested"] += l["qty"] * l["price"]
        p["flows"].append((d(l["buy_date"]), -l["qty"] * l["price"]))
        p["first_date"] = min(p["first_date"], d(l["buy_date"]))
    for p in out.values():
        p["avg_cost"] = p["invested"] / p["qty"] if p["qty"] else None
    return out


def stock_recommendation(summary: dict, weight_pct, first_date, cfg: dict, today: date) -> dict:
    """Action from quality score + risk flags + concentration. Never from purchase price or short-term moves."""
    score, risks, reasons = summary["quant_score"], list(summary["risks"]), []
    h = cfg["horizon_years"]
    close, bench = summary.get("close"), summary.get("bench")
    if close is not None and len(close) > 252:
        n = round(min(h, (close.index[-1] - close.index[0]).days / 365.25) * 252)
        c = finance.cagr(float(close.iloc[-n - 1]), float(close.iloc[-1]), n / 252) if 0 < n < len(close) else None
        if c is not None:
            reasons.append(f"{n / 252:.1f}y price CAGR {c:.1%} (your horizon: {h}y)")
    if score is None:
        return {"action": "Hold - cannot assess (insufficient data)", "reasons": reasons + risks, "score": None}
    reasons.insert(0, f"Quant score {score}/100 (hold >= {cfg['hold_min']}, buy >= {cfg['buy_min']})")
    over = weight_pct is not None and weight_pct > cfg["max_position_pct"]
    if over:
        reasons.append(f"Position is {weight_pct:.1f}% of portfolio, above your {cfg['max_position_pct']:.0f}% limit")
        action = "Trim (concentration)"
    elif score < cfg["hold_min"]:
        action = "Review - consider selling" if risks or score < cfg["hold_min"] - 10 else "Review"
    elif score >= cfg["buy_min"] and not risks and (weight_pct is None or weight_pct < cfg["max_position_pct"] * 0.8):
        action = "Buy more"
    else:
        action = "Hold"
        if score >= cfg["buy_min"] and risks:
            reasons.append("Strong score but risk flags block adding")
    reasons += risks
    if action.startswith(("Review", "Trim")) and first_date and (today - first_date).days < 365:
        reasons.append("Oldest lot held < 1 year: selling may attract short-term capital gains tax")
    return {"action": action, "reasons": reasons, "score": score}


# ---------- assets ----------
def asset_class(a: dict) -> str:
    return KIND_TO_CLASS.get(a["kind"], "Private / other")


def asset_value(a: dict, today: date):
    """(value, basis) - FDs accrue automatically unless a manual value is entered."""
    if a["kind"] == "Fixed deposit" and a.get("current_value") in (None, 0) and a.get("rate_pct") is not None:
        v = finance.fd_value(a["invested"], a["rate_pct"], d(a["start_date"]), today, d(a.get("maturity_date")))
        return v, "estimated (quarterly compounding)"
    return a.get("current_value"), "manual"


def asset_recommendation(a: dict, cfg: dict, today: date) -> dict:
    reasons, action = [], "Hold"
    mat = d(a.get("maturity_date"))
    if a["kind"] == "Fixed deposit":
        if mat and mat <= today:
            action, reasons = "Matured - decide: reinvest or withdraw", [f"Matured on {mat}"]
        elif mat and (mat - today).days <= cfg["fd_alert_days"]:
            action, reasons = "Plan reinvestment", [f"Matures in {(mat - today).days} days"]
        if a.get("rate_pct") is not None:
            real = a["rate_pct"] - cfg["inflation_pct"]
            reasons.append(f"Real return ~{real:+.1f}% (rate {a['rate_pct']}% vs inflation {cfg['inflation_pct']}%)")
            if real < 0 and action == "Hold":
                action = "Hold (safety only) - negative real return"
    elif a["kind"] == "Gold":
        reasons.append("Judge by allocation drift vs your target, not by price moves")
    else:
        reasons.append("Illiquid / self-valued: review at least annually; value is your own estimate")
    upd = d(a.get("updated"))
    if a["kind"] != "Fixed deposit" and upd and (today - upd).days > cfg["stale_value_days"]:
        reasons.append(f"Value not updated for {(today - upd).days} days - refresh it")
    return {"action": action, "reasons": reasons}


# ---------- allocation ----------
def allocation(values_by_class: dict, cfg: dict) -> list[dict]:
    total = sum(values_by_class.values())
    rows = []
    for c in CLASSES:
        actual = values_by_class.get(c, 0) / total * 100 if total else 0.0
        target = cfg["target_allocation"].get(c, 0.0)
        diff = actual - target
        tol = cfg["drift_tolerance_pct"]
        note = ("Overweight - direct new money elsewhere" if diff > tol
                else "Underweight - consider adding" if diff < -tol else "Within target range")
        rows.append({"Class": c, "Value": values_by_class.get(c, 0.0), "Actual %": round(actual, 1),
                     "Target %": target, "Drift (pp)": round(diff, 1), "Note": note})
    return rows


# ---------- orchestration ----------
def analyze_portfolio(cfg: dict, data: dict, fx: dict, today: date | None = None) -> dict:
    """data: stock_lots, funds, fund_lots, sips, assets (lists of row dicts).
    fx: summary(sym)->summary (raises on failure), nav(fund)->Series (raises), bench(sym)->Series|None,
        usd_inr -> float|None. Returns rows for every section plus converted totals."""
    today = today or date.today()
    base, rate = cfg["base_currency"], fx.get("usd_inr")
    warnings, errors, items = [], {}, []

    def conv(x, ccy):
        return finance.convert(x, ccy, base, rate)

    # stocks
    stocks = []
    for sym, pos in aggregate_lots(data.get("stock_lots", [])).items():
        try:
            sm = fx["summary"](sym)
        except Exception as exc:
            errors[sym] = str(exc) or type(exc).__name__
            continue
        ccy = sm["currency"] or pos["currency"] or "?"
        value = pos["qty"] * sm["last_price"]
        same = (pos["currency"] in (None, "", ccy))
        if not same:
            warnings.append(f"{sym}: purchase currency {pos['currency']} differs from market currency {ccy}; P&L not computed.")
        inv = pos["invested"]
        row = {"symbol": sym, "name": sm["name"], "qty": pos["qty"], "avg_cost": pos["avg_cost"], "price": sm["last_price"],
               "currency": ccy, "invested": inv if same else None, "value": value,
               "pnl": value - inv if same else None, "pnl_pct": (value / inv - 1) if same and inv else None,
               "xirr": finance.xirr(pos["flows"] + [(today, value)]) if same else None,
               "first_date": pos["first_date"], "summary": sm}
        stocks.append(row)
        items.append({"class": "Stocks", "name": sym, "currency": ccy, "value": value, "invested": row["invested"], "row": row})

    # mutual funds and SIPs
    funds, sips_out = [], []
    for f in data.get("funds", []):
        try:
            nav = fx["nav"](f)
        except Exception as exc:
            errors[f["name"] or f["code"]] = str(exc) or type(exc).__name__
            continue
        bench = fx["bench"](f["benchmark"]) if f.get("benchmark") else None
        an = mutual_funds.analyse_fund(nav, bench, f.get("category") or "Equity", cfg, f.get("expense_ratio"))
        units, invested, flows = 0.0, 0.0, []
        for l in (x for x in data.get("fund_lots", []) if x["fund_id"] == f["id"]):
            units += l["units"]; invested += l["units"] * l["nav"]; flows.append((d(l["buy_date"]), -l["units"] * l["nav"]))
        for s in (x for x in data.get("sips", []) if x["fund_id"] == f["id"]):
            end = d(s.get("end_date"))
            pos = finance.sip_position(s["amount"], finance.sip_dates(d(s["start_date"]), end, s["day"], today), nav)
            units += pos["units"]; invested += pos["invested"]; flows += pos["flows"]
            active = end is None or end >= today
            if pos["skipped"]:
                warnings.append(f"{f['name']}: {pos['skipped']} SIP instalment(s) skipped (no NAV near the date).")
            sips_out.append({"fund": f["name"] or f["code"], "amount": s["amount"], "day": s["day"], "start": d(s["start_date"]),
                             "end": end, "active": active, "invested": pos["invested"], "value": pos["units"] * an["last_nav"],
                             "currency": f.get("currency") or "INR", "rec": an["rec"] if active else "Ended", "id": s["id"]})
        ccy = f.get("currency") or "INR"
        value = units * an["last_nav"]
        row = {"id": f["id"], "name": f["name"] or f["code"], "category": f.get("category"), "units": units, "invested": invested,
               "value": value, "pnl": value - invested, "pnl_pct": value / invested - 1 if invested else None,
               "xirr": finance.xirr(flows + [(today, value)]) if flows else None, "currency": ccy, "analysis": an}
        funds.append(row)
        if units:
            items.append({"class": "Mutual funds", "name": row["name"], "currency": ccy, "value": value, "invested": invested, "row": row})

    # manual assets
    assets = []
    for a in data.get("assets", []):
        v, basis = asset_value(a, today)
        if v is None:
            warnings.append(f"{a['name']}: no current value entered.")
            continue
        row = {"id": a["id"], "kind": a["kind"], "name": a["name"], "currency": a.get("currency") or "INR", "invested": a.get("invested"),
               "value": v, "basis": basis, "pnl": v - a["invested"] if a.get("invested") else None,
               "rec": asset_recommendation(a, cfg, today)}
        assets.append(row)
        items.append({"class": asset_class(a), "name": a["name"], "currency": row["currency"], "value": v,
                      "invested": a.get("invested"), "row": row})

    # totals in base currency; never combine currencies without a rate
    unconverted, by_class, total, total_inv = [], {}, 0.0, 0.0
    for it in items:
        v = conv(it["value"], it["currency"])
        if v is None:
            unconverted.append(f"{it['name']} ({it['currency']})")
            continue
        it["value_base"] = v
        iv = conv(it["invested"], it["currency"]) if it["invested"] is not None else None
        it["invested_base"] = iv
        by_class[it["class"]] = by_class.get(it["class"], 0) + v
        total += v
        total_inv += iv or 0
    if unconverted:
        warnings.append(f"No {base} conversion available for: {', '.join(unconverted)}. Excluded from totals "
                        "(set a USD/INR rate in Settings if Yahoo is unreachable).")
    for s in stocks:  # recommendations need portfolio weights
        it = next(i for i in items if i["row"] is s)
        w = it.get("value_base", 0) / total * 100 if total and "value_base" in it else None
        s["weight_pct"] = w
        s["rec"] = stock_recommendation(s["summary"], w, s["first_date"], cfg, today)
    return {"stocks": stocks, "funds": funds, "sips": sips_out, "assets": assets, "items": items,
            "total": total, "invested_total": total_inv, "by_class": by_class, "base": base,
            "allocation": allocation(by_class, cfg), "warnings": warnings, "errors": errors,
            "sip_monthly": sum(s["amount"] for s in sips_out if s["active"])}


# ---------- bulk import ----------
def parse_stock_csv(df, today: date | None = None) -> tuple[list[dict], list[str]]:
    """Validate a DataFrame with columns symbol, qty, price, buy_date[, currency]. Returns (rows, errors)."""
    from src import market_data as md
    today = today or date.today()
    cols = {c.strip().lower(): c for c in df.columns}
    missing = [c for c in ("symbol", "qty", "price", "buy_date") if c not in cols]
    if missing:
        return [], [f"Missing column(s): {', '.join(missing)}"]
    rows, errors = [], []
    for i, r in df.iterrows():
        n = i + 2
        sym, err = md.normalize_symbol(str(r[cols["symbol"]]))
        try:
            qty, price = float(r[cols["qty"]]), float(r[cols["price"]])
            bd = date.fromisoformat(str(r[cols["buy_date"]]).strip()[:10])
        except (ValueError, TypeError):
            errors.append(f"Row {n}: qty/price must be numbers and buy_date must be YYYY-MM-DD.")
            continue
        if err or qty <= 0 or price <= 0 or bd > today:
            errors.append(f"Row {n}: {err or 'qty and price must be > 0 and buy_date not in the future.'}")
            continue
        ccy = str(r[cols["currency"]]).strip().upper() if "currency" in cols and str(r[cols["currency"]]).strip() not in ("", "nan") else None
        rows.append({"symbol": sym, "qty": qty, "price": price, "buy_date": bd.isoformat(), "currency": ccy, "notes": None})
    return rows, errors
