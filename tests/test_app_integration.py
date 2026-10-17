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
