"""App-level tests with mocked market data (no network)."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import market_data as md

APP = str(Path(__file__).parent.parent / "app.py")


def fake_hist(n=800):
    idx = pd.date_range("2022-01-01", periods=n)
    close = 100 * np.exp(np.cumsum(np.full(n, 0.0005) + np.sin(np.arange(n)) * 0.005))
    return pd.DataFrame({"Close": close, "Volume": 1000.0}, index=idx)


def run(monkeypatch, hist, info):
    st.cache_data.clear()
    monkeypatch.setattr(md, "fetch_history", lambda s, *a, **k: hist)
    monkeypatch.setattr(md, "fetch_info", lambda s, *a, **k: info)
    at = AppTest.from_file(APP).run(timeout=30)
    next(b for b in at.button if b.label == "Analyse").click().run(timeout=30)
    return at


def test_full_analysis_with_mock_data(monkeypatch):
    info = md.DataResult(data={"returnOnEquity": 0.2, "profitMargins": 0.2, "operatingMargins": 0.25,
                               "revenueGrowth": 0.1, "earningsGrowth": 0.1, "trailingPE": 20, "forwardPE": 18,
                               "debtToEquity": 80, "currentRatio": 1.5, "freeCashflow": 1e9, "currency": "USD"})
    at = run(monkeypatch, md.DataResult(data=fake_hist()), info)
    assert not at.exception
    assert any("Unavailable" in m.value for m in at.metric)  # combined score never faked


def test_missing_fundamentals_degrades_gracefully(monkeypatch):
    at = run(monkeypatch, md.DataResult(data=fake_hist()), md.DataResult(error="No fundamental data available."))
    assert not at.exception
    assert any("Fundamentals unavailable" in w.value for w in at.warning)


def test_history_failure_shows_error(monkeypatch):
    at = run(monkeypatch, md.DataResult(error="No price data found for 'AAPL'."), md.DataResult(error="x"))
    assert not at.exception and at.error


def test_news_flow_combined_score(monkeypatch):
    from src import gemini_analysis as ga, news as nw
    arts = [{"title": "t", "url": "http://u", "summary": "", "source": "", "published": None}]
    monkeypatch.setattr(nw, "collect_news", lambda *a, **k: (arts, []))
    good = {"news_score": 60.0, "sentiment": "neutral", "thesis_change": "unchanged", "confidence": "low",
            "catalysts": [], "risks": [], "evidence_urls": [], "data_limitations": []}
    monkeypatch.setattr(ga, "analyze_news", lambda *a, **k: ga.NewsAnalysis(result=good))
    info = md.DataResult(data={"returnOnEquity": 0.2, "profitMargins": 0.2, "operatingMargins": 0.25,
                               "revenueGrowth": 0.1, "earningsGrowth": 0.1, "trailingPE": 20, "forwardPE": 18,
                               "debtToEquity": 80, "currentRatio": 1.5, "freeCashflow": 1e9})
    at = run(monkeypatch, md.DataResult(data=fake_hist()), info)
    next(b for b in at.button if b.label == "Run news analysis").click().run(timeout=30)
    assert not at.exception
    comb = next(m for m in at.metric if m.label.startswith("Combined"))
    assert comb.value != "Unavailable"


def test_news_failure_keeps_combined_unavailable(monkeypatch):
    from src import gemini_analysis as ga, news as nw
    arts = [{"title": "t", "url": "http://u", "summary": "", "source": "", "published": None}]
    monkeypatch.setattr(nw, "collect_news", lambda *a, **k: (arts, []))
    monkeypatch.setattr(ga, "analyze_news", lambda *a, **k: ga.NewsAnalysis(error="Gemini free-tier quota exhausted"))
    at = run(monkeypatch, md.DataResult(data=fake_hist()), md.DataResult(error="x"))
    next(b for b in at.button if b.label == "Run news analysis").click().run(timeout=30)
    assert not at.exception and at.error
    assert next(m for m in at.metric if m.label.startswith("Combined")).value == "Unavailable"


def test_snapshot_saved_and_watchlist_page(monkeypatch):
    from src import storage
    at = run(monkeypatch, md.DataResult(data=fake_hist()), md.DataResult(error="x"))
    assert storage.research_history("AAPL")[0]["label"].startswith("Incomplete")
    next(b for b in at.button if b.label == "Add to watchlist").click().run(timeout=30)
    assert storage.list_watchlist() == ["AAPL"]
    at.sidebar.radio[0].set_value("Watchlist").run(timeout=30)
    assert not at.exception and at.dataframe


def test_screener_page_runs_with_mock_data(monkeypatch):
    st.cache_data.clear()
    monkeypatch.setattr(md, "fetch_history", lambda s, *a, **k: md.DataResult(data=fake_hist()))
    monkeypatch.setattr(md, "fetch_info", lambda s, *a, **k: md.DataResult(error="none"))
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.radio[0].set_value("Screener").run(timeout=30)
    next(b for b in at.button if b.label == "Run screen").click().run(timeout=60)
    assert not at.exception
    assert any("passed" in m.value for m in at.markdown)


def _seed_portfolio():
    from src import storage
    storage.add_row("stock_lots", {"symbol": "AAPL", "qty": 10, "price": 100.0, "buy_date": "2023-01-01", "currency": "USD"})
    fid = storage.add_row("funds", {"code": "1", "source": "India (AMFI scheme code via mfapi.in)", "name": "Test Fund",
                                    "category": "Equity", "benchmark": "^NSEI", "currency": "INR"})
    storage.add_row("sips", {"fund_id": fid, "amount": 5000, "day": 5, "start_date": "2024-01-05"})
    storage.add_row("assets", {"kind": "Gold", "name": "Gold bars", "currency": "INR", "invested": 100000,
                               "current_value": 150000, "updated": "2025-01-01"})


def test_portfolio_page_end_to_end(monkeypatch):
    from src import mutual_funds as mfm
    st.cache_data.clear()
    _seed_portfolio()
    nav = pd.Series(100 * np.exp(np.cumsum(np.full(1600, 0.0004) + np.sin(np.arange(1600)) * 0.004)),
                    index=pd.bdate_range(end="2025-06-30", periods=1600))
    monkeypatch.setattr(md, "fetch_history", lambda s, *a, **k: md.DataResult(data=fake_hist()))
    monkeypatch.setattr(md, "fetch_info", lambda s, *a, **k: md.DataResult(error="none"))
    monkeypatch.setattr(mfm, "fetch_nav", lambda c, s, **k: md.DataResult(data=nav))
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.radio[0].set_value("Portfolio").run(timeout=60)
    assert not at.exception
    assert any(m.label.startswith("Net worth") for m in at.metric)
    text = " ".join(df.value.to_csv() for df in at.dataframe)
    assert "AAPL" in text and "Gold bars" in text and "Recommendation" in text


def test_portfolio_empty_state(monkeypatch):
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.radio[0].set_value("Portfolio").run(timeout=30)
    assert not at.exception and any("Nothing here yet" in i.value for i in at.info)


def test_add_stock_lot_and_save_settings_via_forms(monkeypatch):
    from src import settings, storage
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.radio[0].set_value("Portfolio").run(timeout=30)
    f = lambda label, kind: next(w for w in getattr(at, kind) if w.label == label)
    f("Ticker", "text_input").set_value("tcs.ns")
    f("Quantity", "number_input").set_value(5.0)
    f("Buy price (per share)", "number_input").set_value(3000.0)
    next(b for b in at.button if b.label == "Add").click().run(timeout=30)
    rows = storage.list_rows("stock_lots")
    assert not at.exception and rows and rows[0]["symbol"] == "TCS.NS" and rows[0]["qty"] == 5
    # invalid input is rejected
    f("Ticker", "text_input").set_value("")
    next(b for b in at.button if b.label == "Add").click().run(timeout=30)
    assert len(storage.list_rows("stock_lots")) == 1 and at.error
    # settings persist
    f("Investment horizon (years)", "number_input").set_value(10)
    next(b for b in at.button if b.label == "Save settings").click().run(timeout=30)
    assert settings.load()["horizon_years"] == 10


def test_overview_shows_holdings_xirr_and_sips(monkeypatch):
    from src import mutual_funds as mfm
    st.cache_data.clear()
    _seed_portfolio()
    nav = pd.Series(100 * np.exp(np.cumsum(np.full(1600, 0.0004))), index=pd.bdate_range(end="2025-06-30", periods=1600))
    monkeypatch.setattr(md, "fetch_history", lambda s, *a, **k: md.DataResult(data=fake_hist()))
    monkeypatch.setattr(md, "fetch_info", lambda s, *a, **k: md.DataResult(error="none"))
    monkeypatch.setattr(mfm, "fetch_nav", lambda c, s, **k: md.DataResult(data=nav))
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.radio[0].set_value("Portfolio").run(timeout=60)
    assert not at.exception
    cols = {c for df in at.dataframe for c in df.value.columns}
    assert {"XIRR", "Monthly amount"} <= cols
    assert any("Test Fund" in df.value.to_csv() and "Monthly amount" in df.value.columns for df in at.dataframe)
