# Project status
**Latest stable phase:** phase-1-quantitative (branch `ccr-01f79ea2-5hbe2r`; commit hash in git log)

## Done
- Phase 0: skeleton, config, GitHub Actions (run on 180aad5: **success**), PowerShell scripts.
- Phase 1: ticker validation, price/volume chart, SMA50/200, RSI, returns, volatility, drawdown, benchmark-relative
  return (S&P 500 / Nifty 50 / Sensex), fundamentals extraction, explainable 0-100 quant score
  (Quality 20, Growth 15, Valuation 15, Health 10, Momentum 10; normalized over available data),
  risk flags blocking Buy, incomplete-data handling. Combined score shown as **Unavailable** until Phase 2.

## Tests actually run (Linux sandbox, Python 3.13)
- `pytest -q`: 35 passed (unit, mocked integration, Streamlit AppTest). Headless Streamlit start: health `ok`, root HTTP 200.
- GitHub Actions for Phase 1: see Actions tab (not yet checked when this file was written).

## Known limitations
- Sandbox blocks Yahoo/Google News/ai.google.dev: **live Yahoo data never exercised**; yfinance field names
  (`info` keys, `debtToEquity` in percent) are from memory and need checking on a real machine.
- Score thresholds are generic (no sector/country calibration; financials skip leverage checks).
- Currency: figures shown in the source's reported currency; no conversion.
- Gemini model ID not verified from official docs; user must set `GEMINI_MODEL`.
- No browser/UI automation performed.

## Pending (needs user)
- Windows verification of `setup.ps1`, `run.ps1`, app with live data (try AAPL, TCS.NS, RELIANCE.BO).

## Next task
Phase 2: `src/news.py` (RSS, dedupe, relevance), `src/gemini_analysis.py` (single bounded call, JSON validation, cache, fallback), mocked tests.
