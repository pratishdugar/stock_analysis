from datetime import date

import numpy as np
import pandas as pd
import pytest

import config
from src import mutual_funds as mf, portfolio as pf

CFG = dict(config.PORTFOLIO_DEFAULTS)
TODAY = date(2025, 6, 30)


def summ(score=80, risks=(), price=100.0, ccy="USD", name="X"):
    return {"quant_score": score, "risks": list(risks), "last_price": price, "currency": ccy, "name": name,
            "close": None, "bench": None}


def test_aggregate_lots():
    lots = [{"symbol": "A", "qty": 10, "price": 100, "buy_date": "2023-01-01", "currency": "USD"},
            {"symbol": "A", "qty": 10, "price": 200, "buy_date": "2022-01-01", "currency": "USD"}]
    p = pf.aggregate_lots(lots)["A"]
    assert p["qty"] == 20 and p["avg_cost"] == 150 and p["first_date"] == date(2022, 1, 1)


@pytest.mark.parametrize("score,risks,weight,expected", [
    (80, [], 5, "Buy more"), (80, [], 14, "Hold"), (80, ["x"], 5, "Hold"), (60, [], 5, "Hold"),
    (50, [], 5, "Review"), (30, [], 5, "Review - consider selling"), (50, ["x"], 5, "Review - consider selling"),
    (90, [], 40, "Trim (concentration)"), (None, [], 5, "Hold - cannot assess (insufficient data)")])
def test_stock_rules(score, risks, weight, expected):
    assert pf.stock_recommendation(summ(score, risks), weight, date(2020, 1, 1), CFG, TODAY)["action"] == expected


def test_recommendation_ignores_purchase_price_and_flags_short_term_tax():
    r = pf.stock_recommendation(summ(30), 5, date(2025, 3, 1), CFG, TODAY)
    assert any("short-term capital gains" in x for x in r["reasons"])


def test_thresholds_are_configurable():
    cfg = {**CFG, "buy_min": 60}
    assert pf.stock_recommendation(summ(65), 5, None, cfg, TODAY)["action"] == "Buy more"


def test_allocation_drift():
    rows = pf.allocation({"Stocks": 700, "Gold": 300}, CFG)
    by = {r["Class"]: r for r in rows}
    assert by["Stocks"]["Note"].startswith("Overweight") and by["Mutual funds"]["Note"].startswith("Underweight")
    assert pf.allocation({}, CFG)[0]["Actual %"] == 0


def test_asset_values_and_recs():
    fd = {"kind": "Fixed deposit", "name": "FD", "invested": 1000, "rate_pct": 7, "start_date": "2024-06-30",
          "maturity_date": "2025-08-01", "current_value": None}
    v, basis = pf.asset_value(fd, TODAY)
    assert v > 1000 and "estimated" in basis
    assert pf.asset_recommendation(fd, CFG, TODAY)["action"] == "Plan reinvestment"
    assert pf.asset_recommendation({**fd, "maturity_date": "2025-01-01"}, CFG, TODAY)["action"].startswith("Matured")
    low = pf.asset_recommendation({**fd, "rate_pct": 3, "maturity_date": None}, CFG, TODAY)
    assert "negative real return" in low["action"]
    priv = {"kind": "Private investment", "name": "Startup", "updated": "2023-01-01"}
    assert any("not updated" in r for r in pf.asset_recommendation(priv, CFG, TODAY)["reasons"])


def nav_series(years=6, daily=0.0004):
    idx = pd.bdate_range(end="2025-06-30", periods=int(years * 261))
    rng = np.random.default_rng(1)
    return pd.Series(100 * np.exp(np.cumsum(daily + rng.normal(0, 0.006, len(idx)))), index=idx)


def test_fund_analysis_scores_and_recs():
    good = mf.analyse_fund(nav_series(daily=0.0008), nav_series(daily=0.0003), "Equity", CFG)
    bad = mf.analyse_fund(nav_series(daily=-0.0002), nav_series(daily=0.0005), "Equity", CFG)
    assert good["window_years"] == 5 and good["score"] > bad["score"]
    assert bad["rec"].startswith("Review") and good["excess"] > 0


def test_fund_too_new_and_horizon_window():
    assert mf.analyse_fund(nav_series(1.5), None, "Equity", CFG)["score"] is None
    assert mf.analyse_fund(nav_series(6), None, "Equity", {**CFG, "horizon_years": 3})["window_years"] == 3


def test_expense_ratio_risk_blocks_continue():
    a = mf.analyse_fund(nav_series(daily=0.0008), nav_series(daily=0.0003), "Equity", CFG, expense_ratio=2.2)
    assert a["risks"] and not a["rec"].startswith("Continue")


def test_parse_mfapi_and_fetch(monkeypatch):
    payload = {"meta": {}, "data": [{"date": "02-01-2024", "nav": "11.5"}, {"date": "01-01-2024", "nav": "10"},
                                    {"date": "bad", "nav": "x"}, {"date": "03-01-2024", "nav": "0"}]}
    s = mf.parse_mfapi(payload)
    assert list(s.values) == [10.0, 11.5] and s.index.is_monotonic_increasing
    assert mf.fetch_nav("1", "India (x)", getter=lambda u: payload).ok
    assert "No NAV" in mf.fetch_nav("1", "India (x)", getter=lambda u: {"data": []}).error
    def boom(u): raise ConnectionError()
    assert not mf.fetch_nav("1", "India (x)", getter=boom).ok
    assert not mf.search_funds("ab").ok
    assert mf.search_funds("axis", getter=lambda u: [{"schemeCode": 1, "schemeName": "Axis"}]).data[0]["code"] == "1"


def fixtures(nav=None):
    nav = nav if nav is not None else nav_series()
    return {"summary": lambda s: {"AAA": summ(80, price=120, ccy="USD", name="AAA Inc"),
                                  "BBB.NS": summ(40, price=500, ccy="INR", name="BBB")}[s],
            "nav": lambda f: nav, "bench": lambda s: nav_series(daily=0.0003), "usd_inr": 80.0}


DATA = {"stock_lots": [{"symbol": "AAA", "qty": 10, "price": 100, "buy_date": "2023-01-01", "currency": "USD"},
                       {"symbol": "BBB.NS", "qty": 10, "price": 600, "buy_date": "2022-01-01", "currency": "INR"}],
        "funds": [{"id": 1, "code": "1", "source": "India", "name": "Fund", "category": "Equity", "benchmark": "^NSEI",
                   "expense_ratio": 0.5, "currency": "INR"}],
        "fund_lots": [{"fund_id": 1, "units": 100, "nav": 100, "buy_date": "2022-01-03"}],
        "sips": [{"id": 1, "fund_id": 1, "amount": 5000, "day": 5, "start_date": "2024-01-05", "end_date": None}],
        "assets": [{"id": 1, "kind": "Gold", "name": "Gold", "currency": "INR", "invested": 100000, "current_value": 150000,
                    "updated": "2025-06-01"},
                   {"id": 2, "kind": "Fixed deposit", "name": "FD", "currency": "INR", "invested": 100000, "rate_pct": 7,
                    "start_date": "2024-06-30", "maturity_date": "2026-06-30", "current_value": None}]}


def test_analyze_portfolio_end_to_end():
    r = pf.analyze_portfolio(CFG, DATA, fixtures(), TODAY)
    st = {s["symbol"]: s for s in r["stocks"]}
    assert st["AAA"]["pnl"] == 200 and st["AAA"]["pnl_pct"] == pytest.approx(0.2)
    assert st["BBB.NS"]["pnl"] == -1000
    assert st["BBB.NS"]["rec"]["action"].startswith("Review")
    assert r["total"] > 0 and r["base"] == "INR" and not r["warnings"]
    assert r["sip_monthly"] == 5000 and r["sips"][0]["invested"] > 0
    assert set(r["by_class"]) == set(pf.CLASSES) - {"Private / other"}
    assert abs(sum(a["Actual %"] for a in r["allocation"]) - 100) < 0.2
    assert sum(s["weight_pct"] for s in r["stocks"]) < 100


def test_missing_fx_excludes_usd_with_warning():
    fx = {**fixtures(), "usd_inr": None}
    r = pf.analyze_portfolio(CFG, DATA, fx, TODAY)
    assert any("AAA" in w and "conversion" in w for w in r["warnings"])
    assert all(i["name"] != "AAA" for i in r["items"] if "value_base" in i)


def test_failures_are_isolated():
    fx = fixtures()
    fx["summary"] = lambda s: (_ for _ in ()).throw(RuntimeError("no data")) if s == "AAA" else summ(60, price=500, ccy="INR")
    fx["nav"] = lambda f: (_ for _ in ()).throw(RuntimeError("nav down"))
    r = pf.analyze_portfolio(CFG, DATA, fx, TODAY)
    assert "AAA" in r["errors"] and "Fund" in r["errors"] and len(r["stocks"]) == 1 and r["assets"]


def test_currency_mismatch_suppresses_pnl():
    data = {**DATA, "stock_lots": [{"symbol": "AAA", "qty": 1, "price": 100, "buy_date": "2023-01-01", "currency": "INR"}]}
    r = pf.analyze_portfolio(CFG, data, fixtures(), TODAY)
    assert r["stocks"][0]["pnl"] is None and any("P&L not computed" in w for w in r["warnings"])


def test_parse_stock_csv():
    df = pd.DataFrame({"Symbol": ["aapl", "TCS.NS", "bad sym", "X"], "qty": [1, 2, 3, -1],
                       "price": [10, 20, 30, 5], "buy_date": ["2023-01-01", "2022-05-05", "2023-01-01", "2023-01-01"],
                       "currency": ["usd", "INR", "INR", "INR"]})
    rows, errs = pf.parse_stock_csv(df, TODAY)
    assert [r["symbol"] for r in rows] == ["AAPL", "TCS.NS"] and rows[0]["currency"] == "USD" and len(errs) == 2
    assert pf.parse_stock_csv(pd.DataFrame({"a": [1]}))[1][0].startswith("Missing")
    bad = pd.DataFrame({"symbol": ["A"], "qty": ["x"], "price": [1], "buy_date": ["2023-01-01"]})
    assert "Row 2" in pf.parse_stock_csv(bad, TODAY)[1][0]
