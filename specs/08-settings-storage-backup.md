# 08 · Settings, storage and backup

## Settings (src/settings.py; defaults in `config.PORTFOLIO_DEFAULTS`)
| Key | Default | Meaning |
|---|---|---|
| horizon_years | 5 | Investment horizon (1–40; UI warns below 5) |
| base_currency | INR | Currency for totals (INR/USD) |
| usd_inr_override | 0 | 0 = live rate from Yahoo, else this rate |
| buy_min / hold_min | 75 / 55 | Stock action thresholds (hold_min < buy_min ≤ 100) |
| max_position_pct | 15 | Single-stock concentration limit (% of net worth) |
| fund_buy_min / fund_hold_min | 65 / 45 | Fund action thresholds |
| risk_free_pct | 7 | FD-like hurdle return for funds |
| inflation_pct | 5 | For FD real-return check |
| drift_tolerance_pct | 5 | Allowed allocation drift (pp) |
| fd_alert_days | 90 | FD maturity warning window |
| stale_value_days | 365 | Manual value staleness warning |
| target_allocation | 30/30/10/20/10 | Stocks/MF/Gold/FD/Private-other; must sum to 100 |

- Settings MUST be validated on save; invalid input is rejected with messages and nothing is stored. ✅T
- If stored settings are unreadable or invalid, defaults are used. ✅T

## Storage (src/storage.py)
- One SQLite file at `<project>/data/stock_research.db` (absolute path, independent of the working directory),
  git-ignored. ✅T
- Every connection MUST be closed after use (open handles lock files on Windows) and commit or roll back as a unit.
- A corrupted file MUST be renamed `*.corrupt` and replaced with a fresh database, never crash the app. ✅T
- Table/column names in generic CRUD are whitelisted. Deleting a fund cascades to its lots and SIPs. ✅T

## Backup (src/backup.py)
- Export MUST include all portfolio tables, the watchlist and settings as one JSON file. ✅T
- Restore MUST validate the whole file first (required fields, fund references, settings) and write everything in
  one transaction — all rows or none. It adds rows; restoring twice duplicates holdings. ✅T
