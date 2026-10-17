# Stock Research App

Personal, free-data-source stock research tool (US + NSE/BSE) for 1-5 year investing. Streamlit UI, explainable scoring, optional Gemini news analysis. **Research aid only - not financial advice.**

> Status: see [PROJECT_STATUS.md](PROJECT_STATUS.md). Windows scripts have **not yet been tested on Windows**.

## Features
- **Analyse**: price/volume chart, SMA, RSI, returns, drawdown, volatility, benchmark-relative return, explainable 0-100 quant score.
- **News (Gemini, optional)**: up to 8 articles in one request; combined score = 0.7 quant + 0.3 news, shown only when both exist.
- **Watchlist**: local SQLite (`data/`, git-ignored), research snapshots, side-by-side compare.
- **Screener**: curated US + NSE list in `src/universe.py`; news analysis only for the top 3.

- **Portfolio**: record stocks (or bulk-import CSV), mutual funds + SIPs, gold, FDs, PPF/NPS, private investments; see
  net worth, P&L, XIRR, allocation vs your targets, and buy/hold/trim/review decisions. Horizon and thresholds are
  configurable under Portfolio > Settings. Your data stays in `data/stock_research.db` on your PC (never committed) -
  use Portfolio > Backup to download a copy.

## Run on Windows (PowerShell)
1. Install [Git](https://git-scm.com/download/win) and [Python 3.12](https://www.python.org/downloads/) (tick "Add python.exe to PATH").
2. `git clone https://github.com/pratishdugar/stock_analysis.git` then `cd stock_analysis`
3. `.\setup.ps1`
   - If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (affects only this window), then retry.
4. (Optional) Open `.env` in Notepad and set `GEMINI_API_KEY` and `GEMINI_MODEL` (get a free key at https://aistudio.google.com/ and a current Flash model ID from Google's model docs). Never share or commit this file.
5. `.\run.ps1` - opens the app in your browser.
6. Tests: `.\.venv\Scripts\python.exe -m pytest`
7. Update later: `git pull`, then `.\setup.ps1` again (safe to re-run).

### Manual equivalent
```
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Ticker formats
US `AAPL`; NSE `RELIANCE.NS`; BSE `RELIANCE.BO` (Yahoo Finance conventions).

## Troubleshooting
- Install fails: check internet/proxy; re-run `.\setup.ps1`.
- "No data" for a ticker: check the suffix; Yahoo may be rate limiting - wait and retry.
- Gemini quota errors: the free tier is limited; the app still shows the quantitative analysis.
