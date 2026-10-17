import json

import pytest

import config
from src import backup, settings, storage


def seed(p):
    fid = storage.add_row("funds", {"code": "1", "source": "India", "name": "F"}, p)
    storage.add_row("sips", {"fund_id": fid, "amount": 100, "day": 5, "start_date": "2024-01-05"}, p)
    storage.add_row("stock_lots", {"symbol": "AAPL", "qty": 1, "price": 1.0, "buy_date": "2024-01-01"}, p)
    storage.add_watchlist("MSFT", p)
    settings.save({**config.PORTFOLIO_DEFAULTS, "horizon_years": 8}, p)


def test_roundtrip_includes_settings_and_watchlist(tmp_path):
    src, dst = tmp_path / "a.db", tmp_path / "b.db"
    seed(src)
    counts = backup.import_all(json.loads(backup.export_all(src)), dst)
    assert counts["funds"] == 1 and counts["sips"] == 1 and counts["stock_lots"] == 1
    sip = storage.list_rows("sips", dst)[0]
    assert sip["fund_id"] == storage.list_rows("funds", dst)[0]["id"]
    assert storage.list_watchlist(dst) == ["MSFT"] and settings.load(dst)["horizon_years"] == 8


@pytest.mark.parametrize("payload", [
    [], {"stock_lots": "x"}, {"stock_lots": [{"symbol": "A"}]},
    {"sips": [{"fund_id": 99, "amount": 1, "day": 1, "start_date": "2024-01-01"}]},
    {"settings": {"buy_min": 10}}])
def test_invalid_backup_writes_nothing(tmp_path, payload):
    p = tmp_path / "c.db"
    with pytest.raises(ValueError):
        backup.import_all(payload, p)
    assert storage.list_rows("stock_lots", p) == [] and storage.list_rows("funds", p) == []


def test_failure_midway_rolls_back(tmp_path, monkeypatch):
    p = tmp_path / "d.db"
    payload = {"stock_lots": [{"symbol": "A", "qty": 1, "price": 1, "buy_date": "2024-01-01"}],
               "assets": [{"kind": "Gold", "name": "G", "invested": object()}]}  # unbindable value -> sqlite error
    with pytest.raises(Exception):
        backup.import_all(payload, p)
    assert storage.list_rows("stock_lots", p) == []
