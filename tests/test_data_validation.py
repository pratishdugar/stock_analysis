import pandas as pd

from src import fundamentals as f, market_data as md


def test_normalize_symbol():
    assert md.normalize_symbol(" reliance.ns ") == ("RELIANCE.NS", None)
    assert md.normalize_symbol("")[0] is None
    assert md.normalize_symbol("AA PL")[0] is None
    assert md.normalize_symbol("M&M.NS")[0] == "M&M.NS"


def test_market_and_benchmark():
    assert md.market_of("TCS.NS") == "NSE" and md.benchmark_for("TCS.NS")[0] == "^NSEI"
    assert md.market_of("X.BO") == "BSE" and md.benchmark_for("X.BO")[0] == "^BSESN"
    assert md.benchmark_for("AAPL")[0] == "^GSPC"


class FakeTicker:
    def __init__(self, hist=None, info=None, exc=None):
        self._h, self._i, self._e = hist, info, exc

    def history(self, **kw):
        if self._e:
            raise self._e
        return self._h

    @property
    def info(self):
        if self._e:
            raise self._e
        return self._i


def factory(**kw):
    return lambda sym: FakeTicker(**kw)


def test_history_ok():
    df = pd.DataFrame({"Close": [1.0, 2.0, 3.0]}, index=pd.date_range("2024-01-01", periods=3, tz="UTC"))
    r = md.fetch_history("AAPL", ticker_factory=factory(hist=df))
    assert r.ok and r.data.index.tz is None


def test_history_empty_invalid_ticker():
    r = md.fetch_history("ZZZZ", ticker_factory=factory(hist=pd.DataFrame()))
    assert not r.ok and "No price data" in r.error


def test_history_insufficient():
    r = md.fetch_history("A", ticker_factory=factory(hist=pd.DataFrame({"Close": [1.0]})))
    assert not r.ok and "Insufficient" in r.error


def test_network_and_rate_limit_errors_do_not_raise():
    r = md.fetch_history("A", ticker_factory=factory(exc=RuntimeError("429 Too Many Requests")))
    assert "Rate limited" in r.error
    r = md.fetch_info("A", ticker_factory=factory(exc=ConnectionError("down")))
    assert not r.ok and "ConnectionError" in r.error


def test_info_empty():
    assert not md.fetch_info("A", ticker_factory=factory(info={})).ok


def test_extract_metrics_handles_missing_and_junk():
    m = f.extract_metrics({"returnOnEquity": 0.2, "trailingPE": float("nan"), "debtToEquity": "x", "sector": "Tech"})
    assert m["roe"] == 0.2 and m["trailing_pe"] is None and m["debt_to_equity"] is None
    assert f.extract_metrics(None)["roe"] is None
