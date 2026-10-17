"""Pure indicator functions on pandas Series of closing prices. No I/O."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(close: pd.Series) -> pd.Series:
    return close.dropna().pct_change().dropna()


def period_return(close: pd.Series, days: int) -> float | None:
    """Total return over the last `days` trading days; None if not enough history."""
    close = close.dropna()
    if days < 1 or len(close) <= days:
        return None
    start = close.iloc[-days - 1]
    if start <= 0:
        return None
    return float(close.iloc[-1] / start - 1)


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI. NaN until `period` changes are available."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    out[(avg_loss == 0) & (avg_gain == 0)] = 50.0
    out[avg_gain.isna() | avg_loss.isna()] = np.nan
    return out


def annualized_volatility(close: pd.Series, min_obs: int = 20) -> float | None:
    r = daily_returns(close)
    if len(r) < min_obs:
        return None
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def max_drawdown(close: pd.Series) -> float | None:
    """Largest peak-to-trough decline as a negative fraction (e.g. -0.35)."""
    close = close.dropna()
    if len(close) < 2:
        return None
    return float((close / close.cummax() - 1).min())


def relative_performance(stock: pd.Series, bench: pd.Series, days: int) -> float | None:
    """Stock period return minus benchmark period return (aligned on common dates)."""
    df = pd.concat([stock, bench], axis=1, join="inner").dropna()
    if df.shape[1] != 2:
        return None
    a = period_return(df.iloc[:, 0], days)
    b = period_return(df.iloc[:, 1], days)
    if a is None or b is None:
        return None
    return a - b
