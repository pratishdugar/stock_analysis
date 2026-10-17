"""Local SQLite persistence: watchlist + one research snapshot per symbol per day.

A corrupted database file is moved aside (.corrupt) and recreated; storage errors never crash the app.
"""
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import date
from pathlib import Path

# Absolute, so the app finds the same database whatever directory it is started from.
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "stock_research.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY, added TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research (
  symbol TEXT NOT NULL, day TEXT NOT NULL, quant_score REAL, coverage REAL, label TEXT,
  news_score REAL, combined_score REAL, currency TEXT, details TEXT,
  PRIMARY KEY (symbol, day));
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS stock_lots (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, qty REAL NOT NULL,
  price REAL NOT NULL, buy_date TEXT NOT NULL, currency TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS funds (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, source TEXT NOT NULL,
  name TEXT, category TEXT, benchmark TEXT, expense_ratio REAL, currency TEXT);
CREATE TABLE IF NOT EXISTS fund_lots (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_id INTEGER NOT NULL,
  units REAL NOT NULL, nav REAL NOT NULL, buy_date TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sips (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_id INTEGER NOT NULL, amount REAL NOT NULL,
  day INTEGER NOT NULL, start_date TEXT NOT NULL, end_date TEXT);
CREATE TABLE IF NOT EXISTS assets (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL,
  currency TEXT, invested REAL, current_value REAL, start_date TEXT, rate_pct REAL, maturity_date TEXT,
  quantity REAL, updated TEXT, notes TEXT);
"""


def _connect(path) -> sqlite3.Connection:
    path = Path(path or DEFAULT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = sqlite3.connect(path)
        con.executescript(_SCHEMA)
        con.execute("SELECT count(*) FROM research").fetchone()
        return con
    except sqlite3.DatabaseError:
        try:
            con.close()
        except Exception:
            pass
        path.replace(path.with_suffix(path.suffix + ".corrupt"))
        con = sqlite3.connect(path)
        con.executescript(_SCHEMA)
        return con


@contextmanager
def _db(path=None):
    """Connection that commits on success, rolls back on error, and is always closed
    (an open handle keeps the file locked on Windows)."""
    with closing(_connect(path)) as con:
        with con:
            yield con


def add_watchlist(symbol: str, path=None) -> None:
    with _db(path) as con:
        con.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?)", (symbol, date.today().isoformat()))


def remove_watchlist(symbol: str, path=None) -> None:
    with _db(path) as con:
        con.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


def list_watchlist(path=None) -> list[str]:
    with _db(path) as con:
        return [r[0] for r in con.execute("SELECT symbol FROM watchlist ORDER BY symbol")]


def save_research(symbol, quant_score, coverage, label, news_score=None, combined_score=None,
                  currency=None, details=None, path=None, day=None) -> None:
    """Upsert one snapshot per symbol per day. A save without a news score keeps the news/combined
    score already stored for that day (the page is re-rendered many times per session)."""
    with _db(path) as con:
        con.execute(
            "INSERT INTO research VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol, day) DO UPDATE SET "
            "quant_score=excluded.quant_score, coverage=excluded.coverage, label=excluded.label, "
            "news_score=COALESCE(excluded.news_score, research.news_score), "
            "combined_score=COALESCE(excluded.combined_score, research.combined_score), "
            "currency=excluded.currency, details=excluded.details",
            (symbol, day or date.today().isoformat(), quant_score, coverage, label, news_score,
             combined_score, currency, json.dumps(details or {})))


def research_history(symbol, limit=30, path=None) -> list[dict]:
    with _db(path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM research WHERE symbol = ? ORDER BY day DESC LIMIT ?",
                           (symbol, limit)).fetchall()
    return [dict(r) for r in rows]


# --- generic CRUD for portfolio tables (table/column names are whitelisted) ---
TABLES = {
    "stock_lots": ["symbol", "qty", "price", "buy_date", "currency", "notes"],
    "funds": ["code", "source", "name", "category", "benchmark", "expense_ratio", "currency"],
    "fund_lots": ["fund_id", "units", "nav", "buy_date"],
    "sips": ["fund_id", "amount", "day", "start_date", "end_date"],
    "assets": ["kind", "name", "currency", "invested", "current_value", "start_date", "rate_pct",
               "maturity_date", "quantity", "updated", "notes"],
}


def add_row(table, values: dict, path=None) -> int:
    cols = [c for c in TABLES[table] if c in values]
    with _db(path) as con:
        cur = con.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                          [values[c] for c in cols])
        return cur.lastrowid


def update_row(table, row_id, values: dict, path=None) -> None:
    cols = [c for c in TABLES[table] if c in values]
    if cols:
        with _db(path) as con:
            con.execute(f"UPDATE {table} SET {', '.join(c + ' = ?' for c in cols)} WHERE id = ?",
                        [values[c] for c in cols] + [row_id])


def list_rows(table, path=None) -> list[dict]:
    with _db(path) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(f"SELECT * FROM {table} ORDER BY id")]


def delete_row(table, row_id, path=None) -> None:
    with _db(path) as con:
        con.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        if table == "funds":  # keep children consistent
            con.execute("DELETE FROM fund_lots WHERE fund_id = ?", (row_id,))
            con.execute("DELETE FROM sips WHERE fund_id = ?", (row_id,))
