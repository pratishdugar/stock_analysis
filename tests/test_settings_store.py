import config
from src import settings, storage


def test_defaults_valid():
    assert settings.validate(config.PORTFOLIO_DEFAULTS) == []


def test_validation_errors():
    s = dict(config.PORTFOLIO_DEFAULTS)
    assert settings.validate({**s, "hold_min": 80})
    assert settings.validate({**s, "base_currency": "EUR"})
    assert settings.validate({**s, "target_allocation": {**s["target_allocation"], "Gold": 50}})
    assert settings.validate({**s, "horizon_years": -1})
    assert settings.validate({**s, "horizon_years": "five"})


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "s.db"
    s = {**config.PORTFOLIO_DEFAULTS, "horizon_years": 10, "max_position_pct": 20.0}
    assert settings.save(s, p) == []
    assert settings.load(p)["horizon_years"] == 10
    assert settings.save({**s, "buy_min": 10}, p)  # invalid: rejected, not stored
    assert settings.load(p)["buy_min"] == 75


def test_load_falls_back_when_stored_invalid(tmp_path):
    p = tmp_path / "s.db"
    with storage._connect(p) as con:
        con.execute("INSERT INTO settings VALUES ('buy_min', '\"junk\"')")
    assert settings.load(p) == config.PORTFOLIO_DEFAULTS


def test_crud(tmp_path):
    p = tmp_path / "c.db"
    i = storage.add_row("stock_lots", {"symbol": "AAPL", "qty": 2, "price": 100.0, "buy_date": "2023-01-01", "currency": "USD"}, p)
    assert storage.list_rows("stock_lots", p)[0]["symbol"] == "AAPL"
    storage.delete_row("stock_lots", i, p)
    assert storage.list_rows("stock_lots", p) == []


def test_deleting_fund_removes_children(tmp_path):
    p = tmp_path / "c.db"
    fid = storage.add_row("funds", {"code": "1", "source": "India", "name": "F"}, p)
    storage.add_row("fund_lots", {"fund_id": fid, "units": 1, "nav": 1, "buy_date": "2024-01-01"}, p)
    storage.add_row("sips", {"fund_id": fid, "amount": 1, "day": 1, "start_date": "2024-01-01"}, p)
    storage.delete_row("funds", fid, p)
    assert storage.list_rows("fund_lots", p) == [] and storage.list_rows("sips", p) == []
