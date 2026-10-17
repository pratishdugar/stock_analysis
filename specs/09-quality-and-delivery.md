# 09 · Quality, delivery and security

## Testing
- `pytest` MUST pass with **no network and no API keys**: all external calls are injected or monkeypatched. ✅T
- Every bug fix SHOULD add a regression test (`tests/test_regressions.py` or the feature's test file).
- UI flows are tested with Streamlit `AppTest` against mocked data (see `tests/CLAUDE.md` for patterns).
- Tests MUST NOT touch the real database (`tests/conftest.py` redirects it to a temp file).

## CI (.github/workflows/tests.yml) — runs on every push and pull request
- Linux job: install, compile/import check, pytest, Streamlit health check.
- Windows job (Windows PowerShell 5.1): `setup.ps1` twice (must be re-runnable and must not overwrite `.env`),
  pytest in the project venv, and `run.ps1` must bring Streamlit to a healthy state.

## Windows scripts
- `setup.ps1`: find Python 3.11+ (prefers 3.12/3.13 via `py`), create/repair `.venv`, install requirements, verify
  imports, create `.env` from `.env.example` only if missing, never print secrets, clear error messages.
- `run.ps1`: start Streamlit with the venv's Python, passing extra arguments through.

## Security and privacy
- No secrets in the repo; `.env` is git-ignored; `.env.example` holds placeholders only. Never log key values.
- Personal financial data stays in `data/` (git-ignored). Nothing is uploaded except news article text sent to
  Gemini when the user clicks.

## Definition of done for a change
1. Spec updated (if behaviour changed). 2. Code + tests. 3. `pytest -q` and `python -m pyflakes` clean.
4. `PROJECT_STATUS.md` and `CHANGELOG.md` updated. 5. Committed and pushed. 6. Both CI jobs green — reported
honestly, never assumed.
