"""Central configuration. Secrets come from the environment / local .env only."""
import os

from dotenv import load_dotenv

load_dotenv()

# Weights for the final score (see PROJECT_STATUS.md).
QUANT_WEIGHT = 0.70
NEWS_WEIGHT = 0.30


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def gemini_model() -> str:
    """Model ID is configured by the user; no model is hardcoded in the code base."""
    return os.getenv("GEMINI_MODEL", "").strip()


def gemini_configured() -> bool:
    return bool(gemini_api_key() and gemini_model())

# Defaults for portfolio analysis. Users change these in the app (Portfolio > Settings);
# saved values live in the local database and override these.
PORTFOLIO_DEFAULTS = {
    "horizon_years": 5,            # investment horizon (at least 5 recommended)
    "base_currency": "INR",        # INR or USD; totals are shown in this currency
    "usd_inr_override": 0.0,       # 0 = fetch live USD/INR from Yahoo; else use this rate
    "buy_min": 75,                 # stock quant score >= this (and no risk flags) -> Buy more
    "hold_min": 55,                # stock quant score < this -> Review
    "max_position_pct": 15.0,      # single stock above this % of portfolio -> Trim (concentration)
    "fund_buy_min": 65,            # fund score >= this -> Continue / add
    "fund_hold_min": 45,           # fund score < this -> Review fund
    "risk_free_pct": 7.0,          # FD-like return used as the hurdle for funds
    "inflation_pct": 5.0,          # used to judge real returns of FDs
    "drift_tolerance_pct": 5.0,    # allocation drift tolerated before flagging
    "fd_alert_days": 90,           # warn when an FD matures within this many days
    "stale_value_days": 365,       # warn when a manually valued asset was not updated for this long
    "target_allocation": {"Stocks": 30, "Mutual funds": 30, "Gold": 10, "Fixed deposits": 20, "Private / other": 10},
}
