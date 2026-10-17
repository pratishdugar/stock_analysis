"""Extract a clean, None-for-missing metrics dict from a Yahoo `info` dict."""
import math

FIELDS = {
    "roe": "returnOnEquity",
    "operating_margin": "operatingMargins",
    "profit_margin": "profitMargins",
    "revenue_growth": "revenueGrowth",
    "earnings_growth": "earningsGrowth",
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "price_to_book": "priceToBook",
    "debt_to_equity": "debtToEquity",  # Yahoo reports percent (150 = 1.5x)
    "current_ratio": "currentRatio",
    "free_cashflow": "freeCashflow",
    "market_cap": "marketCap",
}


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return float(v)


def extract_metrics(info: dict | None) -> dict:
    info = info or {}
    m = {k: _num(info.get(src)) for k, src in FIELDS.items()}
    m["sector"] = info.get("sector") if isinstance(info.get("sector"), str) else None
    m["name"] = info.get("longName") or info.get("shortName")
    m["currency"] = info.get("currency")
    m["financial_currency"] = info.get("financialCurrency")
    return m
