"""Explainable 0-100 quantitative score. Missing inputs are skipped, never zero-filled.

Each component has a max (quality 20, growth 15, valuation 15, health 10, momentum 10 = 70).
Within a component, sub-metrics are averaged (each mapped linearly 0..1) and scaled to
the component max. Components with no usable inputs are 'unavailable'; the score is
normalized over available maxima and flagged incomplete when coverage is low.

LIMITATIONS: thresholds are generic (not sector- or country-calibrated) except that
financial-sector companies skip margin / leverage / liquidity checks.
"""
from dataclasses import dataclass, field

from src import technicals as ta

MAX_POINTS = {"Quality": 20, "Growth": 15, "Valuation": 15, "Financial health": 10, "Momentum": 10}
MIN_COVERAGE = 0.6  # below this share of available weight, score is 'incomplete'
BUY_MIN, HOLD_MIN = 75, 55


def lin(value, lo, hi):
    """Map value linearly to 0..1 (lo->0, hi->1; works for lo > hi to invert)."""
    if value is None:
        return None
    t = (value - lo) / (hi - lo)
    return max(0.0, min(1.0, t))


@dataclass
class Component:
    name: str
    max_points: int
    points: float | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.points is not None


def _build(name, items) -> Component:
    """items: list of (label, value_text, score_0_1_or_None)."""
    c = Component(name, MAX_POINTS[name])
    used = []
    for label, text, s in items:
        if s is None:
            c.notes.append(f"{label}: not available")
        else:
            used.append(s)
            c.notes.append(f"{label}: {text} -> {s:.2f}")
    if used:
        c.points = round(sum(used) / len(used) * c.max_points, 2)
    return c


def _pct(v):
    return None if v is None else f"{v:.1%}"


def momentum_inputs(close, bench=None) -> dict:
    """Derive momentum metrics from price series."""
    out = {"ret_1y": ta.period_return(close, 252), "max_drawdown": ta.max_drawdown(close.tail(756)),
           "above_200dma": None, "rel_1y": None}
    ma = ta.sma(close, 200)
    if len(close) >= 200 and not ma.dropna().empty:
        out["above_200dma"] = bool(close.iloc[-1] > ma.iloc[-1])
    if bench is not None:
        out["rel_1y"] = ta.relative_performance(close, bench, 252)
    return out


def score_stock(metrics: dict, mom: dict) -> dict:
    fin = (metrics.get("sector") or "") == "Financial Services"
    g = metrics.get
    pe_ok = lambda v: None if v is None else (0.0 if v <= 0 else lin(v, 45, 15))
    quality = [("ROE", _pct(g("roe")), lin(g("roe"), 0.05, 0.25))]
    quality.append(("Profit margin", _pct(g("profit_margin")), lin(g("profit_margin"), 0.03, 0.25)))
    if not fin:
        quality.append(("Operating margin", _pct(g("operating_margin")), lin(g("operating_margin"), 0.05, 0.30)))
    growth = [("Revenue growth", _pct(g("revenue_growth")), lin(g("revenue_growth"), 0.0, 0.20)),
              ("Earnings growth", _pct(g("earnings_growth")), lin(g("earnings_growth"), 0.0, 0.25))]
    valuation = [("Trailing P/E", g("trailing_pe"), pe_ok(g("trailing_pe"))),
                 ("Forward P/E", g("forward_pe"), pe_ok(g("forward_pe")))]
    health = []
    if not fin:
        health.append(("Debt/Equity %", g("debt_to_equity"), lin(g("debt_to_equity"), 250, 50)))
        health.append(("Current ratio", g("current_ratio"), lin(g("current_ratio"), 0.8, 2.0)))
        fcf = g("free_cashflow")
        health.append(("Free cash flow", fcf, None if fcf is None else (1.0 if fcf > 0 else 0.0)))
    else:
        health.append(("Leverage/liquidity checks", "skipped for financials", None))
    a200 = mom.get("above_200dma")
    momentum = [("1y return", _pct(mom.get("ret_1y")), lin(mom.get("ret_1y"), -0.10, 0.30)),
                ("Max drawdown (3y)", _pct(mom.get("max_drawdown")), lin(mom.get("max_drawdown"), -0.60, -0.15)),
                ("Above 200-day MA", a200, None if a200 is None else float(a200)),
                ("1y vs benchmark", _pct(mom.get("rel_1y")), lin(mom.get("rel_1y"), -0.10, 0.10))]
    comps = [_build("Quality", quality), _build("Growth", growth), _build("Valuation", valuation),
             _build("Financial health", health), _build("Momentum", momentum)]

    avail_max = sum(c.max_points for c in comps if c.available)
    coverage = avail_max / sum(MAX_POINTS.values())
    score = None
    if avail_max > 0:
        score = round(sum(c.points for c in comps if c.available) / avail_max * 100, 1)
    complete = coverage >= MIN_COVERAGE and score is not None
    risks = risk_flags(metrics, mom, complete)
    return {"quant_score": score if complete else None, "raw_score": score, "complete": complete,
            "coverage": coverage, "components": comps, "risks": risks,
            "label": classify(score if complete else None, risks)}


def risk_flags(metrics: dict, mom: dict, complete: bool) -> list[str]:
    r = []
    if not complete:
        r.append("Insufficient data coverage - assessment incomplete.")
    pe = metrics.get("trailing_pe")
    if pe is not None and pe > 60:
        r.append(f"Very high trailing P/E ({pe:.0f}) - valuation risk.")
    if metrics.get("profit_margin") is not None and metrics["profit_margin"] < 0:
        r.append("Company is currently unprofitable.")
    if (metrics.get("sector") or "") != "Financial Services":
        de = metrics.get("debt_to_equity")
        if de is not None and de > 300:
            r.append(f"Very high debt/equity ({de:.0f}%).")
        if metrics.get("free_cashflow") is not None and metrics["free_cashflow"] < 0:
            r.append("Negative free cash flow.")
    dd = mom.get("max_drawdown")
    if dd is not None and dd < -0.6:
        r.append(f"Severe drawdown ({dd:.0%}) in last 3 years.")
    return r


def classify(score, risks: list[str]) -> str:
    """Preliminary label from the quantitative score only (news not yet included)."""
    if score is None:
        return "Incomplete - insufficient data"
    if score >= BUY_MIN:
        return "Hold / Watchlist (Buy blocked by risk checks)" if risks else "Buy Candidate"
    if score >= HOLD_MIN:
        return "Hold / Watchlist"
    return "Avoid / Sell-Review"


def combine(quant, news):
    """final = 0.70*quant + 0.30*news; None unless both exist (never substitutes quant)."""
    import config
    if quant is None or news is None:
        return None
    return round(config.QUANT_WEIGHT * quant + config.NEWS_WEIGHT * news, 1)
