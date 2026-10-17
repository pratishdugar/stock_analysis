# tests/ — conventions

- Offline only: monkeypatch `md.fetch_history`, `md.fetch_info`, `mutual_funds.fetch_nav`, `news.collect_news`,
  `gemini_analysis.analyze_news`, or pass fake fetchers. Use deterministic synthetic data.
- `conftest.py` (autouse) points `storage.DEFAULT_PATH` at a temp file: tests never touch `data/`.
- Bug fixes: add a test that fails before the fix (`test_regressions.py` or the feature's file).
- Streamlit AppTest patterns (`test_app_integration.py`):
  - `AppTest.from_file(APP).run(timeout=30)` with `APP` an absolute path.
  - Call `st.cache_data.clear()` first when mocks change — cached loaders leak between tests.
  - Find buttons/inputs by label (`next(b for b in at.button if b.label == "...")`); positions change between runs.
  - Switch views with `at.sidebar.radio[0].set_value("Portfolio").run()`.
  - Inspect tables via `df.value.to_csv()` / `df.value.columns` (str(df) truncates).
