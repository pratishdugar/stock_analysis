# Changelog
## Phase 0 - foundation
- Repo skeleton, config, minimal Streamlit page, tests, CI workflow, Windows scripts.

## Phase 1 - quantitative
- Market data, technicals, fundamentals, scoring, UI, 35 tests.

## Phase 2 - news + Gemini
- RSS news, Gemini structured analysis, cache, fallbacks, combined score; 56 tests.

## Phase 3 - watchlist
- SQLite watchlist/history, compare view; 60 tests.

## Phase 4 - screener
- Curated universe + quant screener, capped news step; 65 tests.

## Phase 5 - portfolio
- Stocks, mutual funds + SIPs, gold/FD/private assets, settings, allocation, backup; 104 tests.

## Review & hardening
- Fixed: same-day research re-save wiped the stored news score; DB path depended on the working directory;
  SQLite connections were never closed (Windows file locks); mixed-currency lots produced wrong P&L; weak
  overweight stocks said "Trim" instead of "Review"; fund search crashed on unexpected responses; cash/PPF
  called "illiquid"; "Tata" news matched TCS; benchmark failure crashed portfolio analysis; asset value update
  re-created the row; horizon CAGR missing for the default 5y horizon (row-count window) and never compared to
  the benchmark; Overview lacked XIRR and the SIP list; backup omitted settings/watchlist and restore was not atomic.
- Gemini prompt and app text use the configured horizon; Yahoo fund NAVs unadjusted; dependency major versions capped.
- `setup.ps1` rewritten (robust Python detection, repairs a broken .venv); Windows CI job runs setup/run scripts.
- Added `specs/`, `CLAUDE.md`, `src/CLAUDE.md`, `tests/CLAUDE.md`; 123 tests.
