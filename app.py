"""Stock Research App - Streamlit entry point."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
from src import fundamentals, gemini_analysis, market_data as md, news as news_mod, scoring, technicals as ta

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


with st.sidebar:
    raw = st.text_input("Ticker", value="AAPL", help="US: AAPL | NSE: RELIANCE.NS | BSE: RELIANCE.BO")
    go_btn = st.button("Analyse", type="primary")
    st.markdown("**Examples:** `AAPL`, `MSFT`, `TCS.NS`, `RELIANCE.BO`")
    if config.gemini_configured():
        st.success("Gemini configured.")
    else:
        st.warning("Gemini not configured - app works without it; combined score is unavailable.")

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
