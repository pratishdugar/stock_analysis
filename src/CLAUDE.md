# src/ — pure logic

- No `import streamlit` here. Anything that touches the network takes an injectable fetcher (`getter=`,
  `ticker_factory=`, `client=`, or the `fx` dict in `portfolio.analyze_portfolio`) so tests never hit the network.
- Fetch functions return `market_data.DataResult(data=..., error=...)` instead of raising; UI shows `error`.
- Return `None` for "unknown" (not 0, not NaN). Callers format None as "n/a".
- Module map: `market_data` (symbols, Yahoo prices/info) · `technicals` (indicators) · `fundamentals` (info →
  metrics) · `scoring` (0–100 score, labels, `lin`, `combine`) · `report` (one-stock summary dict) · `news` (RSS) ·
  `gemini_analysis` · `screener` / `universe` · `storage` (SQLite; use `_db()` context manager, it closes the
  connection) · `settings` · `backup` · `finance` (XIRR, CAGR, FD, SIP, FX) · `mutual_funds` · `portfolio`
  (valuation + recommendation rules).
- Rule changes (thresholds, recommendation order) must be mirrored in `specs/` and covered by tests.
- New DB tables: add to `storage._SCHEMA` (CREATE IF NOT EXISTS — existing user DBs must keep working) and to
  `storage.TABLES` if they need generic CRUD/backup. Never drop or rename columns without a migration.
