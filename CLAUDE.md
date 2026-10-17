# CLAUDE.md

Personal stock-research and portfolio app (Streamlit, Python). Read `specs/00-intent.md` first, then the spec
for the area you are changing (`specs/README.md` maps specs → code → tests). Current state and next task:
`PROJECT_STATUS.md`.

## Commands
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows: .\setup.ps1
.venv/bin/python -m pytest -q                                        # all tests: offline, no API keys
.venv/bin/python -m pyflakes app.py ui_portfolio.py config.py src tests
.venv/bin/streamlit run app.py                                      # Windows: .\run.ps1
```
Headless smoke check: `streamlit run app.py --server.headless true --server.port 8599` then
`curl localhost:8599/_stcore/health` → `ok`. Stop it with `kill <pid>` — not `pkill -f "streamlit run"`, which also
kills the shell running the command.

## Layout
- `app.py` — Streamlit entry: Analyse / Watchlist / Screener views; cached loaders `load_history`, `load_info`,
  `summarize_symbol`. `ui_portfolio.py` — Portfolio view (tabs). These are the ONLY files that import streamlit.
- `src/` — pure logic, no Streamlit (see `src/CLAUDE.md`). `config.py` — env (Gemini) + `PORTFOLIO_DEFAULTS`.
- `tests/` — pytest + Streamlit AppTest (see `tests/CLAUDE.md`). `specs/` — intended behaviour.
- `data/` — local SQLite with the user's holdings. Git-ignored. Never commit, print or upload its contents.

## Rules that must not be broken
- Missing data is skipped and marked incomplete — never replaced with 0. Never add amounts in different currencies
  without a rate (`finance.convert` returns None → exclude + warn).
- Recommendations are explainable prompts: always return reasons; never use purchase price; low score → "Review",
  not "Sell". Keep thresholds in settings (`config.PORTFOLIO_DEFAULTS` + Settings tab), not hard-coded.
- The app must work without Gemini; combined score is "Unavailable" unless both scores exist.
- Gemini: model only from `GEMINI_MODEL`; one bounded request per analysis; only on user click; validate output.
- No secrets in code, tests, logs or commits. Never read or print `.env` values. Tests use mocks only.
- Free data sources only (Yahoo/yfinance, RSS, mfapi.in). No paid services, agents, RAG, vector DBs or cloud deploys.

## Workflow (definition of done — `specs/09-quality-and-delivery.md`)
1. Update the relevant spec if behaviour changes. 2. Write a failing test for a bug, then fix.
3. `pytest -q` + pyflakes clean. 4. Update `PROJECT_STATUS.md` (+ one line in `CHANGELOG.md`).
5. Commit, push to the working branch. 6. Check BOTH CI jobs (Linux + Windows) and report results honestly.
Never force-push or rewrite history. Keep changes minimal; match the existing terse style.

## Environment notes
The Claude Code cloud sandbox blocks Yahoo Finance, Google News, mfapi.in and ai.google.dev, so live data cannot be
exercised there — rely on mocks and say so. GitHub Actions (public repo → free) is the clean-room and Windows check.
The user is on a limited budget: prefer low/medium effort, avoid large rewrites and verbose output.
