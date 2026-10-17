import numpy as np
import pandas as pd
import pytest

from src import technicals as ta


def s(vals):
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals)), dtype=float)


def test_period_return():
    assert ta.period_return(s([100, 110, 121]), 2) == pytest.approx(0.21)


def test_period_return_insufficient():
    assert ta.period_return(s([100, 110]), 5) is None
    assert ta.period_return(s([100, 110]), 0) is None


def test_sma():
    out = ta.sma(s([1, 2, 3, 4]), 2)
    assert np.isnan(out.iloc[0]) and out.iloc[3] == 3.5


def test_rsi_all_up_is_100_and_all_down_is_0():
    assert ta.rsi(s(range(1, 40))).iloc[-1] == 100
    assert ta.rsi(s(range(40, 1, -1))).iloc[-1] == pytest.approx(0)


def test_rsi_flat_is_50_and_short_is_nan():
    assert ta.rsi(s([5] * 30)).iloc[-1] == 50
    assert ta.rsi(s([1, 2, 3])).isna().all()


def test_rsi_bounded():
    rng = np.random.default_rng(0)
    r = ta.rsi(s(100 + rng.normal(0, 1, 200).cumsum())).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_max_drawdown():
    assert ta.max_drawdown(s([100, 150, 75, 120])) == pytest.approx(-0.5)
    assert ta.max_drawdown(s([1])) is None


def test_volatility():
    assert ta.annualized_volatility(s([100, 101])) is None
    assert ta.annualized_volatility(s([100.0] * 30)) == 0
    assert ta.annualized_volatility(s(100 * 1.01 ** np.arange(30) * (1 + 0.01 * (-1) ** np.arange(30)))) > 0


def test_relative_performance():
    assert ta.relative_performance(s([100, 120]), s([100, 110]), 1) == pytest.approx(0.10)
    assert ta.relative_performance(s([100, 120]), s([100]), 1) is None


def test_nan_values_ignored():
    assert ta.period_return(s([100, np.nan, 110]), 1) == pytest.approx(0.10)
