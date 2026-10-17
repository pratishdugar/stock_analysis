# Project status
**Latest stable phase:** phase-5-portfolio (branch `ccr-01f79ea2-5hbe2r`; commit hash in git log)

## Done
- Phase 0: skeleton, config, GitHub Actions (run on 180aad5: **success**), PowerShell scripts.
- Phase 1: ticker validation, price/volume chart, SMA50/200, RSI, returns, volatility, drawdown, benchmark-relative
  return (S&P 500 / Nifty 50 / Sensex), fundamentals extraction, explainable 0-100 quant score
  (Quality 20, Growth 15, Valuation 15, Health 10, Momentum 10; normalized over available data),
  risk flags blocking Buy, incomplete-data handling. Combined score shown as **Unavailable** until Phase 2.

- Phase 2: RSS news (Google News + Yahoo for US), dedupe, relevance filter, max 8 articles; single bounded Gemini
  request (google-genai, model from `GEMINI_MODEL`), strict JSON validation (hallucinated URLs dropped), 6h in-memory cache,
  quota/key/model/malformed fallbacks; combined score = 0.7*quant + 0.3*news only when both exist.
  Also fixed UI bug: analysis disappeared on any later click (ticker now kept in session state).

- Phase 3: SQLite (`data/stock_research.db`, git-ignored) watchlist, daily research snapshots, history expander,
  Watchlist view with multi-stock comparison table + rebased price chart; corrupted DB is moved aside and recreated.

- Phase 4: curated 30-stock universe (`src/universe.py`), quant-first screener with filters (score, coverage, risk
  flags, drawdown), cached data, Gemini news only on demand for top 3 (hard cap).

- Phase 5 (portfolio, one commit): Portfolio view with tabs - Overview & decisions, Stocks (lots, CSV import, P&L, XIRR),
  Mutual funds & SIPs (mfapi.in / Yahoo NAV, lump sums, SIPs with NAV-derived units, fund score + recommendation),
  Gold/FD/PPF/private/real estate/cash (manual values, FD accrual), Settings (horizon, thresholds, max position %,
  target allocation, USD/INR; defaults in `config.PORTFOLIO_DEFAULTS`), Backup (JSON export/restore).
  Rule-based Buy more / Hold / Trim / Review per stock, Continue / Hold / Review per fund, allocation drift.
  Data is local (`data/`, git-ignored). Totals only combine INR/USD with a known rate; otherwise excluded with a warning.

## Tests actually run (Linux sandbox, Python 3.13)
- `pytest -q`: 104 passed (unit, mocked integration, Streamlit AppTest). Headless Streamlit start: health `ok`, root HTTP 200.
- GitHub Actions for Phase 1: see Actions tab (not yet checked when this file was written).

## Known limitations
- Sandbox blocks Yahoo/Google News/ai.google.dev: **live Yahoo data never exercised**; yfinance field names
  (`info` keys, `debtToEquity` in percent) are from memory and need checking on a real machine.
- Score thresholds are generic (no sector/country calibration; financials skip leverage checks).
- Currency: figures shown in the source's reported currency; no conversion.
- Gemini never called for real (no key, mocks only); RSS never fetched live. Gemini model ID not verified from official docs; user must set `GEMINI_MODEL`.
- No browser/UI automation performed.

- mfapi.in endpoints/response format and the Yahoo `INR=X` symbol are from memory and never exercised live.
- Portfolio recommendations ignore tax, exit loads, dividends; fund analysis has no category-peer ranking.
- Only INR and USD supported.

## Pending (needs user)
- Windows verification of `setup.ps1`, `run.ps1`, app with live data (try AAPL, TCS.NS, RELIANCE.BO).

## Next task
All planned phases are implemented. Next: user verifies on Windows with live data, reports bugs; then consider
sector-calibrated thresholds, FX-aware comparison, and merging this branch to `main` (open a PR).
