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
    at.button[0].click().run(timeout=30)
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
