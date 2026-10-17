from datetime import date

import pandas as pd
import pytest

from src import finance as f


def test_cagr():
    assert f.cagr(100, 200, 5) == pytest.approx(0.1487, abs=1e-4)
    assert f.cagr(0, 100, 1) is None and f.cagr(100, 100, 0) is None


def test_xirr_simple_year():
    r = f.xirr([(date(2024, 1, 1), -1000), (date(2025, 1, 1), 1100)])
    assert r == pytest.approx(0.10, abs=0.002)


def test_xirr_none_cases():
    assert f.xirr([(date(2024, 1, 1), -1000)]) is None
    assert f.xirr([(date(2024, 1, 1), -1000), (date(2024, 1, 20), 1100)]) is None  # too short
    assert f.xirr([(date(2024, 1, 1), 1000), (date(2025, 1, 1), 1100)]) is None  # no outflow


def test_fd_value():
    v = f.fd_value(1000, 8, date(2024, 1, 1), date(2025, 1, 1))
    assert v == pytest.approx(1000 * 1.02 ** 4, rel=1e-3)
    # stops accruing at maturity
    assert f.fd_value(1000, 8, date(2024, 1, 1), date(2030, 1, 1), date(2025, 1, 1)) == pytest.approx(v, rel=1e-6)
    assert f.fd_value(None, 8, date(2024, 1, 1), date(2025, 1, 1)) is None


def test_sip_dates_clamp_and_bounds():
    ds = f.sip_dates(date(2024, 1, 31), None, 31, date(2024, 4, 30))
    assert ds == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31), date(2024, 4, 30)]
    assert f.sip_dates(date(2024, 1, 15), date(2024, 2, 20), 10, date(2024, 12, 1)) == [date(2024, 2, 10)]


def test_sip_position_skips_missing_nav():
    nav = pd.Series([10.0, 20.0], index=pd.to_datetime(["2024-01-01", "2024-02-01"]))
    p = f.sip_position(1000, [date(2024, 1, 1), date(2024, 2, 1), date(2024, 6, 1)], nav)
    assert p["units"] == pytest.approx(150) and p["invested"] == 2000 and p["skipped"] == 1


def test_convert():
    assert f.convert(10, "USD", "INR", 80) == 800 and f.convert(800, "INR", "USD", 80) == 10
    assert f.convert(5, "INR", "INR", None) == 5
    assert f.convert(5, "USD", "INR", None) is None and f.convert(5, "EUR", "INR", 80) is None
