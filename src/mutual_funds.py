"""Mutual fund NAV retrieval (India: mfapi.in free API; others: Yahoo ticker) and fund analysis.

LIMITATIONS: no category-peer ranking, no expense ratio or manager data unless the user enters the
expense ratio. Benchmark defaults to Nifty 50 / S&P 500, which is inappropriate for debt funds.
"""
from datetime import date, datetime

import pandas as pd

from src import finance, scoring, technicals as ta
from src.market_data import DataResult

MFAPI = "https://api.mfapi.in/mf"
SOURCES = ["India (AMFI scheme code via mfapi.in)", "Yahoo ticker (e.g. VFIAX)"]
CATEGORIES = ["Equity", "Hybrid", "Debt", "Other"]


def _get_json(url):
    import requests
    r = requests.get(url, timeout=15, headers={"User-Agent": "stock-research-app/0.1"})
    r.raise_for_status()
    return r.json()


def search_funds(query: str, getter=None) -> DataResult:
    from urllib.parse import quote_plus
    if len((query or "").strip()) < 3:
        return DataResult(error="Type at least 3 characters to search.")
    try:
        rows = (getter or _get_json)(f"{MFAPI}/search?q={quote_plus(query.strip())}")
    except Exception as exc:
        return DataResult(error=f"Fund search failed ({type(exc).__name__}).")
    if not isinstance(rows, list):
        return DataResult(error="Fund search returned an unexpected response.")
    out = [{"code": str(r["schemeCode"]), "name": str(r.get("schemeName", r["schemeCode"]))}
           for r in rows if isinstance(r, dict) and "schemeCode" in r]
    return DataResult(data=out) if out else DataResult(error="No funds matched.")


def parse_mfapi(payload: dict) -> pd.Series:
    rows = []
    for r in payload.get("data", []):
        try:
            rows.append((datetime.strptime(r["date"], "%d-%m-%Y"), float(r["nav"])))
        except (KeyError, ValueError, TypeError):
            continue
    s = pd.Series(dict(rows), dtype=float).sort_index()
    return s[s > 0]


def fetch_nav(code: str, source: str, getter=None, ticker_factory=None) -> DataResult:
    """data = pd.Series of NAV indexed by date (ascending)."""
    try:
        if source.startswith("India"):
            nav = parse_mfapi((getter or _get_json)(f"{MFAPI}/{code}"))
        else:
            if ticker_factory is None:
                import yfinance as yf
                ticker_factory = yf.Ticker
            # Unadjusted prices: units bought on a date must use that day's actual NAV.
            df = ticker_factory(code).history(period="max", auto_adjust=False)
            nav = df["Close"].dropna() if df is not None and not df.empty else pd.Series(dtype=float)
            if getattr(nav.index, "tz", None) is not None:
                nav.index = nav.index.tz_localize(None)
    except Exception as exc:
        return DataResult(error=f"Could not fetch NAV ({type(exc).__name__}).")
    if len(nav) < 2:
        return DataResult(error=f"No NAV history found for '{code}'. Check the scheme code/ticker.")
    return DataResult(data=nav)


def _cagr_window(nav: pd.Series, years: int):
    end_d = nav.index[-1].date()
    start_d = date.fromordinal(end_d.toordinal() - round(years * 365.25))
    start = finance.nav_on_or_after(nav, start_d, max_gap_days=10)
    return finance.cagr(start, float(nav.iloc[-1]), years)


def analyse_fund(nav: pd.Series, bench: pd.Series | None, category: str, cfg: dict,
                 expense_ratio: float | None = None) -> dict:
    """Score 0-100 from return vs hurdle/benchmark (50), risk-adjusted return (25), drawdown (25)."""
    years_avail = (nav.index[-1] - nav.index[0]).days / 365.25
    window = 5 if (years_avail >= 5 and cfg["horizon_years"] >= 5) else 3 if years_avail >= 3 else None
    out = {"score": None, "window_years": window, "cagr": None, "bench_cagr": None, "excess": None,
           "volatility": None, "max_drawdown": None, "reasons": [], "risks": [],
           "rec": "Not enough history (< 3 years) - cannot assess", "last_nav": float(nav.iloc[-1]),
           "last_date": nav.index[-1].date()}
    if window is None:
        return out
    rf = cfg["risk_free_pct"] / 100
    sl = nav[nav.index >= nav.index[-1] - pd.Timedelta(days=round(window * 365.25))]
    cagr = _cagr_window(nav, window)
    vol, dd = ta.annualized_volatility(sl), ta.max_drawdown(sl)
    out.update(cagr=cagr, volatility=vol, max_drawdown=dd)
    if cagr is None or vol is None or dd is None:
        out["rec"] = "Insufficient data - cannot assess"
        return out
    debt = category in ("Debt",)
    if bench is not None and not debt and len(bench) > 2:
        b = _cagr_window(bench, window)
        out["bench_cagr"] = b
        if b is not None:
            out["excess"] = cagr - b
    if out["excess"] is not None:
        ret_s = scoring.lin(out["excess"], -0.03, 0.03)
        out["reasons"].append(f"{window}y CAGR {cagr:.1%} vs benchmark {out['bench_cagr']:.1%} ({out['excess']:+.1%}/yr)")
    elif debt:
        ret_s = scoring.lin(cagr, rf - 0.02, rf + 0.01)
        out["reasons"].append(f"{window}y CAGR {cagr:.1%} vs {rf:.1%} FD-like hurdle")
    else:
        ret_s = scoring.lin(cagr, rf, rf + 0.08)
        out["reasons"].append(f"{window}y CAGR {cagr:.1%} (no benchmark data; compared with {rf:.1%} hurdle)")
    sharpe = (cagr - rf) / vol if vol > 0 else None
    risk_s = scoring.lin(sharpe, 0.0, 0.7)
    dd_s = scoring.lin(dd, -0.20, -0.02) if debt or category == "Hybrid" else scoring.lin(dd, -0.45, -0.15)
    out["reasons"].append(f"volatility {vol:.1%}, max drawdown {dd:.1%}, return/risk {sharpe if sharpe is None else round(sharpe, 2)}")
    parts = [(ret_s, 50), (risk_s, 25), (dd_s, 25)]
    avail = [(s, w) for s, w in parts if s is not None]
    out["score"] = round(sum(s * w for s, w in avail) / sum(w for _, w in avail) * 100, 1)
    if expense_ratio is not None and expense_ratio > (1.0 if debt else 1.5):
        out["risks"].append(f"Expense ratio {expense_ratio:.2f}% is high for this category; compare with a direct/index alternative.")
    if dd < -0.4 and not debt:
        out["risks"].append(f"Deep drawdown ({dd:.0%}) in the evaluation window.")
    sc = out["score"]
    out["rec"] = ("Continue SIP / add more" if sc >= cfg["fund_buy_min"] and not out["risks"]
                  else "Hold / continue" if sc >= cfg["fund_hold_min"]
                  else "Review fund (compare with category peers)")
    return out
