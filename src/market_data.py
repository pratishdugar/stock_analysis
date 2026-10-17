"""Symbol validation and market-data retrieval (Yahoo Finance via yfinance).

Data is unofficial, may be delayed, incomplete, or wrong. Failures are returned
as DataResult(error=...) instead of raising, so the UI never crashes.
"""
import re
from dataclasses import dataclass

import pandas as pd

SYMBOL_RE = re.compile(r"^[A-Z0-9^][A-Z0-9.\-&]{0,19}$")


@dataclass
class DataResult:
    data: object = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.data is not None


def normalize_symbol(raw: str) -> tuple[str | None, str | None]:
    """Return (symbol, error). Uppercases and validates the format only."""
    sym = (raw or "").strip().upper()
    if not sym:
        return None, "Enter a ticker symbol, e.g. AAPL, RELIANCE.NS or RELIANCE.BO."
    if not SYMBOL_RE.match(sym):
        return None, f"'{sym}' is not a valid ticker format."
    return sym, None


def market_of(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    return "US/other"


def benchmark_for(symbol: str) -> tuple[str, str]:
    """(benchmark symbol, display name) by market."""
    m = market_of(symbol)
    if m == "NSE":
        return "^NSEI", "Nifty 50"
    if m == "BSE":
        return "^BSESN", "BSE Sensex"
    return "^GSPC", "S&P 500"


def _classify_error(exc: Exception) -> str:
    msg = str(exc)
    if "429" in msg or "Too Many Requests" in msg or "rate" in msg.lower():
        return "Rate limited by the data source. Wait a few minutes and retry."
    return f"Could not fetch data ({type(exc).__name__}). Check your connection and the ticker."


def fetch_history(symbol: str, period: str = "5y", ticker_factory=None) -> DataResult:
    """Daily OHLCV (split/dividend adjusted). `ticker_factory` is injectable for tests."""
    try:
        if ticker_factory is None:
            import yfinance as yf
            ticker_factory = yf.Ticker
        df = ticker_factory(symbol).history(period=period, auto_adjust=True)
    except Exception as exc:  # network, rate limit, parsing
        return DataResult(error=_classify_error(exc))
    if df is None or df.empty or "Close" not in df:
        return DataResult(error=f"No price data found for '{symbol}'. Check the ticker and its suffix.")
    df = df.dropna(subset=["Close"])
    if len(df) < 2:
        return DataResult(error=f"Insufficient price history for '{symbol}'.")
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return DataResult(data=df)


def fetch_info(symbol: str, ticker_factory=None) -> DataResult:
    """Fundamentals/valuation dict from Yahoo; may be partial or empty."""
    try:
        if ticker_factory is None:
            import yfinance as yf
            ticker_factory = yf.Ticker
        info = ticker_factory(symbol).info
    except Exception as exc:
        return DataResult(error=_classify_error(exc))
    if not isinstance(info, dict) or not info:
        return DataResult(error="No fundamental data available.")
    return DataResult(data=info)
