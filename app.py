"""Stock Research App - Streamlit entry point."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
from src import fundamentals, gemini_analysis, market_data as md, news as news_mod, report, scoring, screener, storage, universe, technicals as ta

st.set_page_config(page_title="Stock Research", page_icon="📈", layout="wide")
st.title("📈 Stock Research")
st.caption("Personal long-term (1-5 year) research tool. Not financial advice. "
           "Data from Yahoo Finance (unofficial; may be delayed or incomplete).")


@st.cache_data(ttl=3600, show_spinner=False)
def load_history(symbol):
    r = md.fetch_history(symbol)
    return r.data, r.error


@st.cache_data(ttl=3600, show_spinner=False)
def load_info(symbol):
    r = md.fetch_info(symbol)
    return r.data, r.error


def fmt_pct(v):
    return "n/a" if v is None else f"{v:.1%}"


def safe_storage(fn, *a, default=None, **k):
    try:
        return fn(*a, **k)
    except Exception as exc:  # storage must never crash the app
        st.sidebar.warning(f"Local storage problem ({type(exc).__name__}); feature skipped.")
        return default


def watchlist_page():
    st.subheader("Watchlist & comparison")
    wl = safe_storage(storage.list_watchlist, default=[])
    if not wl:
        st.info("Your watchlist is empty. Analyse a stock and click **Add to watchlist**.")
        return
    picked = st.multiselect("Compare / manage", wl, default=wl[:4], max_selections=6)
    if st.button("Remove selected from watchlist") and picked:
        for p in picked:
            safe_storage(storage.remove_watchlist, p)
        st.rerun()
    rows, fig = [], go.Figure()
    for sym in picked:
        h, herr = load_history(sym)
        if herr:
            rows.append({"Symbol": sym, "Label": f"Data error: {herr}"})
            continue
        i, ierr = load_info(sym)
        b, _ = load_history(md.benchmark_for(sym)[0])
        sm = report.build_summary(sym, h, md.DataResult(data=i, error=ierr) if not ierr else md.DataResult(error=ierr),
                                  b["Close"] if b is not None else None)
        rows.append({"Symbol": sym, "Market": sm["market"], "Currency": sm["currency"] or "?",
                     "Quant score": "Incomplete" if sm["quant_score"] is None else sm["quant_score"],
                     "Coverage": f"{sm['coverage']:.0%}", "1y return": fmt_pct(sm["ret_1y"]),
                     "Max drawdown (3y)": fmt_pct(sm["max_drawdown"]), "Label (quant only)": sm["label"]})
        c = h["Close"].tail(504)
        fig.add_trace(go.Scatter(x=c.index, y=c / c.iloc[0] * 100, name=sym))
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Scores are comparable only as rough screens: generic thresholds, prices in different "
                   "currencies are shown rebased to 100 (no FX conversion needed for the chart).")
    if fig.data:
        fig.update_layout(height=400, yaxis_title="Rebased price (start = 100, ~2y)")
        st.plotly_chart(fig, width="stretch")


def summarize_symbol(sym):
    h, herr = load_history(sym)
    if herr:
        raise RuntimeError(herr)
    i, ierr = load_info(sym)
    b, _ = load_history(md.benchmark_for(sym)[0])
    return report.build_summary(sym, h, md.DataResult(data=i, error=ierr) if not ierr else md.DataResult(error=ierr),
                                b["Close"] if b is not None else None)


def screener_page():
    st.subheader("Curated screener")
    st.caption("Quantitative pre-filter over a small hand-picked list (src/universe.py). Not a recommendation list. "
               "Generic thresholds, unofficial data; news analysis runs only on the top 3 shortlisted names, on demand.")
    uni = st.selectbox("Universe", list(universe.UNIVERSES))
    c1, c2, c3 = st.columns(3)
    min_score = c1.slider("Min quant score", 0, 100, 55)
    min_cov = c2.slider("Min data coverage", 0.3, 1.0, 0.6)
    excl = c3.checkbox("Exclude names with risk flags", value=True)
    if st.button("Run screen"):
        bar = st.progress(0.0, text="Fetching data (cached for 1h)...")
        summaries, errors = screener.run_screen(universe.UNIVERSES[uni], summarize_symbol, bar.progress)
        bar.empty()
        st.session_state["screen"] = (summaries, errors)
    if "screen" not in st.session_state:
        return
    summaries, errors = st.session_state["screen"]
    cands = screener.filter_candidates(summaries, min_score, min_cov, exclude_risks=excl)
    st.write(f"{len(cands)} of {len(summaries)} stocks passed" + (f"; {len(errors)} failed to load." if errors else "."))
    if errors:
        st.warning("; ".join(f"{k}: {v}" for k, v in errors.items()))
    if cands:
        st.dataframe(pd.DataFrame([{"Symbol": s["symbol"], "Name": s["name"], "Currency": s["currency"] or "?",
                                    "Quant score": s["quant_score"], "Coverage": f"{s['coverage']:.0%}",
                                    "1y return": fmt_pct(s["ret_1y"]), "Max drawdown (3y)": fmt_pct(s["max_drawdown"]),
                                    "Label (quant only)": s["label"]} for s in cands]), hide_index=True)
        if config.gemini_configured() and st.button(f"Run news analysis on top {len(screener.news_shortlist(cands))}"):
            for s in screener.news_shortlist(cands):
                arts, _ = news_mod.collect_news(s["symbol"], s["name"])
                na = gemini_analysis.analyze_news(s["symbol"], arts)
                st.write(f"**{s['symbol']}**: " + (f"news score {na.result['news_score']:.0f}, "
                         f"combined {scoring.combine(s['quant_score'], na.result['news_score'])}" if na.ok else na.error))


with st.sidebar:
    view = st.radio("View", ["Analyse", "Watchlist", "Screener"], horizontal=True)
    raw = st.text_input("Ticker", value="AAPL", help="US: AAPL | NSE: RELIANCE.NS | BSE: RELIANCE.BO")
    go_btn = st.button("Analyse", type="primary")
    st.markdown("**Examples:** `AAPL`, `MSFT`, `TCS.NS`, `RELIANCE.BO`")
    if config.gemini_configured():
        st.success("Gemini configured.")
    else:
        st.warning("Gemini not configured - app works without it; combined score is unavailable.")

if view == "Watchlist":
    watchlist_page()
    st.stop()
if view == "Screener":
    screener_page()
    st.stop()

if go_btn:
    st.session_state["active_ticker"] = raw
raw = st.session_state.get("active_ticker")
if not raw:
    st.info("Enter a ticker in the sidebar and press **Analyse**.")
    st.stop()

symbol, err = md.normalize_symbol(raw)
if err:
    st.error(err)
    st.stop()

with st.spinner(f"Loading {symbol}..."):
    hist, herr = load_history(symbol)
    info, ierr = load_info(symbol)
if herr:
    st.error(herr)
    st.stop()

close = hist["Close"]
metrics = fundamentals.extract_metrics(info if not ierr else None)
currency = metrics.get("currency") or "unknown currency"
bsym, bname = md.benchmark_for(symbol)
bhist, _ = load_history(bsym)
bench = bhist["Close"] if bhist is not None else None

st.subheader(f"{metrics.get('name') or symbol} ({symbol}, {md.market_of(symbol)})")
st.caption(f"Prices in {currency}. Last data point: {close.index[-1].date()}. "
           f"Benchmark: {bname} ({bsym})." + (" Benchmark data unavailable." if bench is None else ""))
if ierr:
    st.warning(f"Fundamentals unavailable: {ierr} Score will be based on price data only and may be incomplete.")
if len(close) < 252:
    st.warning(f"Only {len(close)} trading days of history; long-period metrics are unavailable.")

result = scoring.score_stock(metrics, scoring.momentum_inputs(close, bench))

c1, c2, c3 = st.columns(3)
c1.metric("Quantitative score (70% weight)",
          "Incomplete" if result["quant_score"] is None else f"{result['quant_score']}/100")
news_state = st.session_state.get(f"news_{symbol}")
news_score = news_state.result["news_score"] if news_state and news_state.ok else None
combined = scoring.combine(result["quant_score"], news_score)
c2.metric("Combined score (70% quant + 30% news)", "Unavailable" if combined is None else f"{combined}/100",
          help="Needs a complete quantitative score and a successful news analysis.")
c3.metric("Data coverage", f"{result['coverage']:.0%}")
st.markdown(f"**Preliminary label (quantitative only):** {result['label']}")
st.caption("Thresholds: >=75 Buy Candidate, 55-74 Hold/Watchlist, <55 Avoid/Sell-Review. "
           "A low score on a stock you own means *review*, not an automatic sell.")
for r in result["risks"]:
    st.warning(r)

safe_storage(storage.save_research, symbol, result["quant_score"], result["coverage"], result["label"],
             news_score, combined, metrics.get("currency"), {"risks": result["risks"]})
if st.button("Add to watchlist"):
    safe_storage(storage.add_watchlist, symbol)
    st.success(f"{symbol} added to watchlist.")
past = safe_storage(storage.research_history, symbol, 10, default=[])
if len(past) > 1:
    with st.expander("Previous research snapshots (local)"):
        st.dataframe(pd.DataFrame(past)[["day", "quant_score", "news_score", "combined_score", "label"]],
                     hide_index=True)

tab1, tab2, tab3, tab4 = st.tabs(["Price & indicators", "Score breakdown", "Fundamentals", "News (Gemini)"])

with tab1:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
    fig.add_trace(go.Scatter(x=close.index, y=close, name="Close"), row=1, col=1)
    for w in (50, 200):
        fig.add_trace(go.Scatter(x=close.index, y=ta.sma(close, w), name=f"SMA {w}"), row=1, col=1)
    fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume"), row=2, col=1)
    fig.update_layout(height=550, margin=dict(l=10, r=10, t=10, b=10))
    fig.update_yaxes(title_text=f"Price ({currency})", row=1, col=1)
    st.plotly_chart(fig, width="stretch")
    rows = {f"Return {label}": ta.period_return(close, d)
            for label, d in (("1m", 21), ("3m", 63), ("6m", 126), ("1y", 252), ("3y", 756))}
    rows[f"1y vs {bname}"] = ta.relative_performance(close, bench, 252) if bench is not None else None
    rows["Max drawdown (3y)"] = ta.max_drawdown(close.tail(756))
    rows["Annualized volatility"] = ta.annualized_volatility(close)
    st.table(pd.DataFrame({"Value": {k: fmt_pct(v) for k, v in rows.items()}}))
    rsi_last = ta.rsi(close).dropna()
    st.write("RSI(14):", "n/a" if rsi_last.empty else f"{rsi_last.iloc[-1]:.1f}")

with tab2:
    for c in result["components"]:
        pts = "unavailable" if not c.available else f"{c.points}/{c.max_points}"
        with st.expander(f"{c.name}: {pts}", expanded=False):
            for n in c.notes:
                st.write("- " + n)
    st.caption("Limitations: generic thresholds (not calibrated per sector/country); financial-sector "
               "companies skip margin/leverage checks; missing metrics are skipped, never treated as zero.")

with tab3:
    st.caption(f"Financial figures reported in {metrics.get('financial_currency') or 'unknown currency'}; "
               "ratios are unitless. Fiscal-year conventions differ between US and India.")
    show = {k: v for k, v in metrics.items() if k not in ("name",)}
    st.table(pd.DataFrame({"Value": {k: ("n/a" if v is None else str(v)) for k, v in show.items()}}))

with tab4:
    st.caption("Fetches up to 8 recent relevant articles and sends them in ONE Gemini request "
               "(uses your free-tier quota; results cached 6h). News is evidence, not instructions.")
    if st.button("Run news analysis"):
        with st.spinner("Collecting news..."):
            arts, warns = news_mod.collect_news(symbol, metrics.get("name"))
        for w in warns:
            st.warning(w)
        st.session_state[f"arts_{symbol}"] = arts
        if arts:
            with st.spinner("Asking Gemini..."):
                st.session_state[f"news_{symbol}"] = gemini_analysis.analyze_news(symbol, arts)
        st.rerun()
    arts = st.session_state.get(f"arts_{symbol}", [])
    na = st.session_state.get(f"news_{symbol}")
    if na is not None and not na.ok:
        st.error(na.error + " Combined score stays unavailable; the quantitative score is unchanged.")
    elif na is not None:
        r = na.result
        st.metric("News score", f"{r['news_score']:.0f}/100")
        st.write(f"**Sentiment:** {r['sentiment']} | **Thesis change:** {r['thesis_change']} | "
                 f"**Confidence:** {r['confidence']}" + (" | (cached)" if na.from_cache else ""))
        for title, key in (("Catalysts", "catalysts"), ("Risks", "risks"), ("Data limitations", "data_limitations")):
            if r[key]:
                st.markdown(f"**{title}**\n" + "\n".join(f"- {x}" for x in r[key]))
        if r["evidence_urls"]:
            st.markdown("**Evidence**\n" + "\n".join(f"- {u}" for u in r["evidence_urls"]))
    for a in arts:
        d = a["published"].date() if a["published"] else "date unknown"
        st.markdown(f"- [{a['title']}]({a['url']}) ({d})")
