import pytest

from src import storage


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Never touch the real local database during tests."""
    monkeypatch.setattr(storage, "DEFAULT_PATH", tmp_path / "default.db")
