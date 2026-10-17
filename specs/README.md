# Specifications

These files record **what the app is for and how each feature must behave**. They are the reference for future
changes: change the spec first (or together with the code), then the code, then the tests.

| Spec | Covers | Main code | Main tests |
|---|---|---|---|
| [00-intent](00-intent.md) | Purpose, users, principles, constraints, non-goals | whole repo | — |
| [01-market-analysis](01-market-analysis.md) | Ticker input, price data, indicators, quantitative score | `src/market_data.py`, `technicals.py`, `fundamentals.py`, `scoring.py`, `app.py` | `test_technicals`, `test_scoring`, `test_data_validation` |
| [02-news-gemini](02-news-gemini.md) | News collection, Gemini analysis, combined score | `src/news.py`, `gemini_analysis.py` | `test_news`, `test_gemini_analysis` |
| [03-watchlist-history](03-watchlist-history.md) | Watchlist, research snapshots, comparison | `src/storage.py`, `app.py` | `test_storage` |
| [04-screener](04-screener.md) | Curated universe screening | `src/screener.py`, `universe.py` | `test_screener` |
| [05-portfolio-stocks](05-portfolio-stocks.md) | Stock holdings, P&L, XIRR, stock recommendations | `src/portfolio.py`, `ui_portfolio.py` | `test_portfolio`, `test_regressions` |
| [06-mutual-funds-sips](06-mutual-funds-sips.md) | Funds, lump sums, SIPs, fund recommendations | `src/mutual_funds.py`, `finance.py` | `test_portfolio`, `test_finance` |
| [07-other-assets-allocation](07-other-assets-allocation.md) | Gold, FDs, PPF, private assets, net worth, allocation | `src/portfolio.py` | `test_portfolio` |
| [08-settings-storage-backup](08-settings-storage-backup.md) | Configurable settings, local DB, backup/restore | `src/settings.py`, `storage.py`, `backup.py` | `test_settings_store`, `test_backup` |
| [09-quality-and-delivery](09-quality-and-delivery.md) | Testing, CI, Windows scripts, security, definition of done | `tests/`, `.github/`, `*.ps1` | all |

Wording: **MUST** = required behaviour (covered by tests where marked ✅T); **SHOULD** = expected unless there is a
documented reason; **Limitation** = known gap, deliberately accepted for now.
