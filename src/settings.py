"""User-configurable portfolio settings: defaults in config.py, overrides stored locally."""
import copy
import json

import config
from src import storage

CURRENCIES = {"INR", "USD"}


def validate(s: dict) -> list[str]:
    e = []
    num = lambda k: isinstance(s.get(k), (int, float)) and not isinstance(s.get(k), bool)
    for k in ("horizon_years", "buy_min", "hold_min", "max_position_pct", "fund_buy_min", "fund_hold_min",
              "risk_free_pct", "inflation_pct", "drift_tolerance_pct", "fd_alert_days", "stale_value_days",
              "usd_inr_override"):
        if not num(k) or s[k] < 0:
            e.append(f"'{k}' must be a non-negative number.")
    if e:
        return e
    if not 1 <= s["horizon_years"] <= 40:
        e.append("Horizon must be between 1 and 40 years.")
    if s["hold_min"] >= s["buy_min"] or s["buy_min"] > 100:
        e.append("Stock thresholds must satisfy hold_min < buy_min <= 100.")
    if s["fund_hold_min"] >= s["fund_buy_min"] or s["fund_buy_min"] > 100:
        e.append("Fund thresholds must satisfy fund_hold_min < fund_buy_min <= 100.")
    if not 0 < s["max_position_pct"] <= 100:
        e.append("Max position % must be between 0 and 100.")
    if s.get("base_currency") not in CURRENCIES:
        e.append("Base currency must be INR or USD.")
    t = s.get("target_allocation")
    if not isinstance(t, dict) or set(t) != set(config.PORTFOLIO_DEFAULTS["target_allocation"]):
        e.append("Target allocation must list every asset class.")
    elif any(not isinstance(v, (int, float)) or v < 0 for v in t.values()) or abs(sum(t.values()) - 100) > 0.5:
        e.append("Target allocation must be non-negative and sum to 100%.")
    return e


def load(path=None) -> dict:
    """Defaults overlaid with stored values. Saved sets were validated on save; if the stored set is
    unreadable or invalid (e.g. hand-edited), fall back to defaults."""
    defaults = copy.deepcopy(config.PORTFOLIO_DEFAULTS)
    try:
        with storage._connect(path) as con:
            rows = con.execute("SELECT key, value FROM settings").fetchall()
        merged = {**defaults, **{k: json.loads(v) for k, v in rows if k in defaults}}
        return merged if not validate(merged) else defaults
    except Exception:
        return defaults


def save(s: dict, path=None) -> list[str]:
    errs = validate(s)
    if errs:
        return errs
    with storage._connect(path) as con:
        for k in config.PORTFOLIO_DEFAULTS:
            con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (k, json.dumps(s[k])))
    return []
