"""Regression tests for bugs found in the code review (each failed before its fix)."""
from datetime import date

import pandas as pd

import config
from src import mutual_funds as mf, news, portfolio as pf, storage

CFG = dict(config.PORTFOLIO_DEFAULTS)
TODAY = date(2025, 6, 30)


def test_resaving_snapshot_keeps_earlier_news_score(tmp_path):
    p = tmp_path / "r.db"
    storage.save_research("AAPL", 70, 0.9, "Hold", news_score=60, combined_score=67, path=p, day="2025-01-01")
    storage.save_research("AAPL", 71, 0.9, "Hold", path=p, day="2025-01-01")  # later rerun without news
    row = storage.research_history("AAPL", path=p)[0]
    assert row["quant_score"] == 71 and row["news_score"] == 60 and row["combined_score"] == 67


def test_default_db_path_does_not_depend_on_working_directory():
    import importlib
    fresh = importlib.reload(storage)
    try:
        assert fresh.DEFAULT_PATH.is_absolute()
    finally:
        importlib.reload(storage)


def test_update_row_keeps_id(tmp_path):
    p = tmp_path / "u.db"
    i = storage.add_row("assets", {"kind": "Gold", "name": "G", "invested": 1, "current_value": 1}, p)
    storage.update_row("assets", i, {"current_value": 5, "updated": "2025-01-01"}, p)
    rows = storage.list_rows("assets", p)
    assert len(rows) == 1 and rows[0]["id"] == i and rows[0]["current_value"] == 5


def test_mixed_currency_lots_do_not_produce_pnl():
    lots = [{"symbol": "A", "qty": 1, "price": 100, "buy_date": "2023-01-01", "currency": "USD"},
            {"symbol": "A", "qty": 1, "price": 8000, "buy_date": "2023-02-01", "currency": "INR"}]
    fx = {"summary": lambda s: {"quant_score": 60, "risks": [], "last_price": 120.0, "currency": "USD", "name": "A",
                                "close": None, "bench": None}, "nav": None, "bench": None, "usd_inr": 80}
    r = pf.analyze_portfolio(CFG, {"stock_lots": lots}, fx, TODAY)
    assert r["stocks"][0]["pnl"] is None
    assert any("mixed" in w.lower() or "differs" in w for w in r["warnings"])


def test_weak_overweight_position_is_review_not_just_trim():
    s = {"quant_score": 30, "risks": ["x"], "close": None, "bench": None}
    assert pf.stock_recommendation(s, 40, None, CFG, TODAY)["action"].startswith("Review")


def test_fund_search_handles_unexpected_payload():
    assert not mf.search_funds("axis", getter=lambda u: {"error": "down"}).ok
    assert not mf.search_funds("axis", getter=lambda u: ["junk", 3]).ok


def test_cash_and_ppf_are_not_called_illiquid():
    for kind in ("Cash / savings", "PPF / EPF / NPS"):
        reasons = pf.asset_recommendation({"kind": kind, "name": "x"}, CFG, TODAY)["reasons"]
        assert not any("Illiquid" in r for r in reasons)


def test_relevance_does_not_match_group_name_alone():
    a = {"title": "Tata Motors shares jump", "summary": ""}
    assert not news.is_relevant(a, "TCS.NS", "Tata Consultancy Services Limited")
    assert news.is_relevant({"title": "TCS wins deal", "summary": ""}, "TCS.NS", "Tata Consultancy Services Limited")
    assert news.is_relevant({"title": "Apple unveils", "summary": ""}, "AAPL", "Apple Inc.")


def test_benchmark_failure_does_not_crash_portfolio():
    idx = pd.bdate_range(end="2025-06-30", periods=1000)
    nav = pd.Series(range(100, 1100), index=idx, dtype=float)
    data = {"funds": [{"id": 1, "code": "1", "source": "India", "name": "F", "category": "Equity",
                       "benchmark": "^NSEI", "currency": "INR"}],
            "fund_lots": [{"fund_id": 1, "units": 1, "nav": 100, "buy_date": "2022-01-03"}]}
    def boom(s):
        raise RuntimeError("bench down")
    r = pf.analyze_portfolio(CFG, data, {"nav": lambda f: nav, "bench": boom, "usd_inr": 80}, TODAY)
    assert len(r["funds"]) == 1 and r["funds"][0]["analysis"]["bench_cagr"] is None


def test_gemini_prompt_uses_configured_horizon():
    from src import gemini_analysis as ga
    arts = [{"title": "t", "url": "http://u", "summary": "", "source": "", "published": None}]
    assert "10+ year" in ga.build_prompt("AAPL", arts, horizon_years=10)


def test_horizon_cagr_shown_for_default_5y_horizon_and_compared_to_benchmark():
    idx = pd.bdate_range(end="2025-06-30", periods=1257)  # ~5y of trading days, like the app's 5y fetch
    close = pd.Series(100 * 1.10 ** ((idx - idx[0]).days / 365.25), index=idx)
    bench = pd.Series(100 * 1.15 ** ((idx - idx[0]).days / 365.25), index=idx)
    s = {"quant_score": 60, "risks": [], "close": close, "bench": bench}
    reasons = " ".join(pf.stock_recommendation(s, 5, None, CFG, TODAY)["reasons"])
    assert "price CAGR 10.0%" in reasons and "benchmark 15.0%" in reasons
