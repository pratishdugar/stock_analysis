# 07 · Portfolio — gold, FDs, other assets, net worth and allocation

## Intent
Complete the picture of all investments so allocation and net worth are right, with simple prompts for each asset.

## Asset types and valuation
Gold, Fixed deposit, PPF / EPF / NPS, Private investment, Real estate, Cash / savings, Other. Each has name,
currency, amount invested, start date and optional notes/quantity.
- FD: value auto-estimated with quarterly compounding from principal, rate and start date, stopping at maturity,
  unless a current value is entered. ✅T
- Everything else: a current value entered by the user; values can be updated in place (row identity kept). ✅T

## Prompts (src/portfolio.py `asset_recommendation`)
- FD: matured → "Matured – decide: reinvest or withdraw"; matures within `fd_alert_days` (90) → "Plan
  reinvestment"; rate − inflation < 0 → "Hold (safety only) – negative real return". ✅T
- Gold: judge by allocation drift, not price moves. Cash: keep an emergency fund; excess loses to inflation.
  PPF/EPF/NPS: long lock-in; judge by allocation. Private / real estate / other: illiquid, self-valued, review
  annually. ✅T
- Any manually valued asset not updated for `stale_value_days` (365) → "refresh it". ✅T

## Net worth and allocation
- Classes: Stocks, Mutual funds, Gold, Fixed deposits, Private / other (all other asset types).
- Totals are in the base currency (INR or USD). USD↔INR uses the manual rate in Settings if set, else Yahoo
  `INR=X`. Items whose currency cannot be converted are **excluded with a warning**, never added unconverted. ✅T
- Allocation table: actual % vs target %; drift beyond `drift_tolerance_pct` (5 pp) → Overweight ("direct new money
  elsewhere") / Underweight ("consider adding"). ✅T
- Overview shows net worth, invested (where known), unrealised P&L, active SIPs per month, an allocation chart,
  holdings tables and one decisions table for every holding and drifted class. ✅T

## Limitations
Only INR and USD. Gold price is not fetched automatically. Liabilities (loans) are not tracked.
