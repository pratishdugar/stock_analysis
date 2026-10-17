import config
from src import scoring as sc

GOOD = dict(roe=0.30, profit_margin=0.30, operating_margin=0.35, revenue_growth=0.25, earnings_growth=0.3,
            trailing_pe=12, forward_pe=10, debt_to_equity=30, current_ratio=2.5, free_cashflow=1e9, sector="Technology")
GOOD_MOM = dict(ret_1y=0.4, max_drawdown=-0.1, above_200dma=True, rel_1y=0.2)
BAD = dict(roe=0.0, profit_margin=-0.1, operating_margin=-0.1, revenue_growth=-0.2, earnings_growth=-0.5,
           trailing_pe=-5, forward_pe=80, debt_to_equity=400, current_ratio=0.3, free_cashflow=-1, sector="Technology")
BAD_MOM = dict(ret_1y=-0.5, max_drawdown=-0.8, above_200dma=False, rel_1y=-0.4)


def test_lin():
    assert sc.lin(5, 0, 10) == 0.5 and sc.lin(-1, 0, 10) == 0 and sc.lin(99, 0, 10) == 1
    assert sc.lin(50, 250, 50) == 1 and sc.lin(None, 0, 1) is None


def test_good_stock_buy_candidate():
    r = sc.score_stock(GOOD, GOOD_MOM)
    assert r["complete"] and r["quant_score"] == 100 and r["label"] == "Buy Candidate"


def test_bad_stock_avoid_with_risks():
    r = sc.score_stock(BAD, BAD_MOM)
    assert r["label"] == "Avoid / Sell-Review" and r["risks"]


def test_risk_blocks_buy():
    r = sc.score_stock({**GOOD, "trailing_pe": 70, "forward_pe": 12}, GOOD_MOM)
    assert r["quant_score"] >= 75 and "blocked" in r["label"]


def test_missing_data_is_incomplete_not_zero():
    r = sc.score_stock({}, dict(ret_1y=0.4, max_drawdown=-0.1, above_200dma=True, rel_1y=None))
    assert not r["complete"] and r["quant_score"] is None
    assert r["label"].startswith("Incomplete") and r["coverage"] == 10 / 70


def test_partial_data_skips_missing_metrics():
    r = sc.score_stock({"roe": 0.25}, GOOD_MOM)
    q = next(c for c in r["components"] if c.name == "Quality")
    assert q.points == 20 and any("not available" in n for n in q.notes)
    assert not next(c for c in r["components"] if c.name == "Growth").available


def test_financials_skip_leverage():
    r = sc.score_stock({**GOOD, "sector": "Financial Services", "debt_to_equity": 900}, GOOD_MOM)
    assert not any("debt/equity" in x.lower() for x in r["risks"])


def test_classification_thresholds():
    assert sc.classify(75, []) == "Buy Candidate"
    assert sc.classify(74.9, []) == "Hold / Watchlist"
    assert sc.classify(55, []) == "Hold / Watchlist"
    assert sc.classify(54.9, []) == "Avoid / Sell-Review"


def test_combine_never_substitutes_quant():
    assert sc.combine(80, None) is None and sc.combine(None, 50) is None
    assert sc.combine(80, 50) == round(config.QUANT_WEIGHT * 80 + config.NEWS_WEIGHT * 50, 1) == 71.0


def test_momentum_inputs_short_history():
    import pandas as pd
    m = sc.momentum_inputs(pd.Series([1.0, 2, 3]))
    assert m["ret_1y"] is None and m["above_200dma"] is None
