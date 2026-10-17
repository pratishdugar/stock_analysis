"""JSON backup/restore of everything the user typed in: portfolio tables, watchlist and settings.

Restore is all-or-nothing: the payload is validated first and written in a single transaction.
It adds rows (it never deletes existing ones), so restoring the same file twice duplicates holdings.
"""
import json
from datetime import date

import config
from src import settings as settings_mod, storage

VERSION = 1
_REQUIRED = {"stock_lots": ("symbol", "qty", "price", "buy_date"), "funds": ("id", "code", "source"),
             "fund_lots": ("fund_id", "units", "nav", "buy_date"), "sips": ("fund_id", "amount", "day", "start_date"),
             "assets": ("kind", "name")}


def export_all(path=None) -> str:
    payload = {"version": VERSION, "exported": date.today().isoformat(),
               **{t: storage.list_rows(t, path) for t in storage.TABLES},
               "watchlist": storage.list_watchlist(path), "settings": settings_mod.load(path)}
    return json.dumps(payload, indent=1, default=str)


def validate(payload) -> list[str]:
    if not isinstance(payload, dict):
        return ["Backup file must contain a JSON object."]
    errs = []
    for t, req in _REQUIRED.items():
        rows = payload.get(t, [])
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            errs.append(f"'{t}' must be a list of objects.")
            continue
        for i, r in enumerate(rows, 1):
            missing = [c for c in req if r.get(c) in (None, "")]
            if missing:
                errs.append(f"{t} row {i}: missing {', '.join(missing)}.")
    fund_ids = {r.get("id") for r in payload.get("funds", []) if isinstance(r, dict)}
    for t in ("fund_lots", "sips"):
        for i, r in enumerate(payload.get(t, []) if isinstance(payload.get(t), list) else [], 1):
            if isinstance(r, dict) and r.get("fund_id") not in fund_ids:
                errs.append(f"{t} row {i}: refers to a fund that is not in the backup.")
    if "settings" in payload and settings_mod.validate({**settings_mod.load(), **payload["settings"]}
                                                       if isinstance(payload["settings"], dict) else {}):
        errs.append("Settings in the backup are invalid.")
    if not isinstance(payload.get("watchlist", []), list):
        errs.append("'watchlist' must be a list.")
    return errs


def import_all(payload, path=None) -> dict:
    """Returns {table: rows added}. Raises ValueError (nothing written) if the payload is invalid."""
    errs = validate(payload)
    if errs:
        raise ValueError("; ".join(errs[:5]))

    def insert(con, table, row):
        cols = [c for c in storage.TABLES[table] if c in row]
        cur = con.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                          [row[c] for c in cols])
        return cur.lastrowid

    counts = {}
    with storage._db(path) as con:  # one transaction: all rows or none
        idmap = {f["id"]: insert(con, "funds", f) for f in payload.get("funds", [])}
        counts["funds"] = len(idmap)
        for t in ("stock_lots", "assets"):
            for row in payload.get(t, []):
                insert(con, t, row)
            counts[t] = len(payload.get(t, []))
        for t in ("fund_lots", "sips"):
            for row in payload.get(t, []):
                insert(con, t, {**row, "fund_id": idmap[row["fund_id"]]})
            counts[t] = len(payload.get(t, []))
        for sym in payload.get("watchlist", []):
            con.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?)", (str(sym), date.today().isoformat()))
        if "settings" in payload:
            merged = {**settings_mod.load(path), **payload["settings"]}
            for k in config.PORTFOLIO_DEFAULTS:
                con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (k, json.dumps(merged[k])))
    return counts
