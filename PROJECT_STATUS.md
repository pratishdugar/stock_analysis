# Project status
**Latest stable phase:** phase-5-portfolio + review/hardening pass (branch `ccr-01f79ea2-5hbe2r`; hash in `git log`).
`main` contains only Phase 0 (PR #1); all later work is on the branch and not yet merged.

## Done
- Phases 0–4: foundation, quantitative analysis, news + Gemini, watchlist/history, curated screener.
- Phase 5: Portfolio (stocks, mutual funds + SIPs, gold/FD/PPF/private/cash, net worth, allocation, settings, backup).
- Review pass: 12 bugs fixed with regression tests (see CHANGELOG), Windows CI job added, `specs/` and
  `CLAUDE.md` files added. Behaviour is specified in `specs/`.

## Tests actually run (Linux sandbox, Python 3.13; pandas 3.0, streamlit 1.66, yfinance 1.7, google-genai 2.31)
- `pytest -q`: 123 passed. `pyflakes`: clean. Headless Streamlit start: health `ok`.
- GitHub Actions: Linux job and Windows job (setup.ps1 ×2, pytest, run.ps1 health check) — see the latest run in
  the Actions tab; results are recorded in the phase report, never assumed.

## Known limitations
- Sandbox blocks Yahoo, Google News, mfapi.in and ai.google.dev: **live data paths have never been exercised**
  (yfinance `info` keys, mfapi.in format, `INR=X` rate are from memory). Gemini never called for real.
- Generic score thresholds; no fund peer ranking; INR/USD only; no tax, dividends or exit loads; gold price manual.
- No browser automation beyond Streamlit AppTest.

## Pending (needs user)
- Run on the Windows PC with live data (AAPL, TCS.NS, RELIANCE.BO; a mutual fund search; an SIP); report errors.
- Optionally add `GEMINI_API_KEY` and a current Flash `GEMINI_MODEL` to `.env` and try the News tab.
- Decide whether to merge the branch into `main` (open a PR).

## Next task
Fix whatever live-data issues the user reports from Windows; then consider sector-aware thresholds and fund
category-peer comparison.
