"""Local SQLite persistence: watchlist + one research snapshot per symbol per day.

A corrupted database file is moved aside (.corrupt) and recreated; storage errors never crash the app.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path("data") / "stock_research.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY, added TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research (
  symbol TEXT NOT NULL, day TEXT NOT NULL, quant_score REAL, coverage REAL, label TEXT,
  news_score REAL, combined_score REAL, currency TEXT, details TEXT,
  PRIMARY KEY (symbol, day));
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


def add_watchlist(symbol: str, path=None) -> None:
    with _connect(path) as con:
        con.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?)", (symbol, date.today().isoformat()))


def remove_watchlist(symbol: str, path=None) -> None:
    with _connect(path) as con:
        con.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


def list_watchlist(path=None) -> list[str]:
    with _connect(path) as con:
        return [r[0] for r in con.execute("SELECT symbol FROM watchlist ORDER BY symbol")]


def save_research(symbol, quant_score, coverage, label, news_score=None, combined_score=None,
                  currency=None, details=None, path=None, day=None) -> None:
    """Upsert today's snapshot. A later news score for the same day updates the row."""
    with _connect(path) as con:
        con.execute("INSERT OR REPLACE INTO research VALUES (?,?,?,?,?,?,?,?,?)",
                    (symbol, day or date.today().isoformat(), quant_score, coverage, label, news_score,
                     combined_score, currency, json.dumps(details or {})))


def research_history(symbol, limit=30, path=None) -> list[dict]:
    with _connect(path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM research WHERE symbol = ? ORDER BY day DESC LIMIT ?",
                           (symbol, limit)).fetchall()
    return [dict(r) for r in rows]
