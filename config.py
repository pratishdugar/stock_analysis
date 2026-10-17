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
