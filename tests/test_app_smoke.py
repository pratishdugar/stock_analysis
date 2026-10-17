from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_renders_without_exception():
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py")).run(timeout=30)
    assert not at.exception
    assert at.title[0].value.endswith("Stock Research")
