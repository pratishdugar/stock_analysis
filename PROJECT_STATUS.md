# Project status
**Latest stable phase:** phase-0-foundation (see git log / tags for the commit; branch `ccr-01f79ea2-5hbe2r`)

## Done
- Phase 0: skeleton, `config.py`, minimal app, GitHub Actions workflow, `setup.ps1`/`run.ps1`.

## Tests actually run (Linux sandbox, Python 3.13)
- `pytest -q`: 4 passed. Streamlit headless start: `/_stcore/health` returned `ok`.
- GitHub Actions: see the Actions tab (result recorded in the phase report).

## Environment limits found
- Sandbox blocks Yahoo Finance, Google News and ai.google.dev: **live data and Gemini docs could not be checked**. Phase 1+ tests must use mocks; live checks must happen on the user's machine/CI.
- Gemini model ID not verified from official docs; user must set `GEMINI_MODEL` (no hardcoded default).

## Pending
- Windows verification of `setup.ps1`, `run.ps1`, and the app (needs user's PC).
- Browser/UI automation not performed.

## Next task
Phase 1: market data, technicals, fundamentals, quantitative score (`src/market_data.py`, `technicals.py`, `fundamentals.py`, `scoring.py`).
