# 04 · Curated screener

## Intent
Suggest a short list of candidates to research from a small, hand-picked universe — without burning API quota.

## Requirements
- Universe MUST be a small editable list (`src/universe.py`): 15 US + 15 NSE large caps, unique, valid symbols. ✅T
- Screening MUST be quantitative only; one stock failing to load MUST not stop the run. ✅T
- Filters: minimum quant score (default 55), minimum coverage (default 60%), exclude risk-flagged names (default on),
  3y drawdown no worse than −60%; incomplete scores are excluded; results sorted by score. ✅T
- Optional news analysis MUST run only on demand and on at most **3** top candidates (hard cap). ✅T
- The page MUST say the list is not a recommendation list and that thresholds are generic.
