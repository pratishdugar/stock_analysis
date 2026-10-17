# 05 · Portfolio — stocks

## Intent
Let the user record every stock purchase and see value, profit/loss and a long-term action for each holding.

## Data entry
- A purchase ("lot") = ticker, quantity > 0, price > 0, buy date (not in the future), currency (INR/USD).
  Invalid input is rejected with a message. ✅T
- Bulk import from CSV with columns `symbol, qty, price, buy_date (YYYY-MM-DD)[, currency]`; invalid rows are listed
  by row number and skipped; valid rows can then be imported. ✅T
- Lots can be deleted individually.

## Valuation (per symbol, in the stock's own currency)
- Quantity, average cost, last price, invested, value, P&L, P&L %, XIRR (money-weighted annual return; shown only
  when the cash flows span ≥ 90 days) and weight in the total portfolio. ✅T
- If lots were entered in different currencies, or the purchase currency differs from the market currency, P&L and
  XIRR MUST NOT be computed; a warning explains why. ✅T

## Recommendation rules (src/portfolio.py `stock_recommendation`)
Inputs: quant score and risk flags (spec 01), weight %, settings (spec 08). Evaluated in order:

| Condition | Action |
|---|---|
| Score unavailable | Hold – cannot assess (insufficient data) |
| Score < `hold_min` (55) and (risk flags or score < `hold_min` − 10) | Review – consider selling |
| Score < `hold_min` | Review |
| Weight > `max_position_pct` (15%) | Trim (concentration) |
| Score ≥ `buy_min` (75), no risk flags, weight < 80% of the max | Buy more |
| Otherwise | Hold (with "risk flags block adding" when relevant) |

- Reasons MUST include the score vs thresholds, the price CAGR over the user's horizon (by calendar date, capped by
  available history) vs the benchmark's CAGR over the same dates, and any risk flags; "lagging the market" is noted
  when more than 3%/yr behind. ✅T
- When an action suggests selling or trimming and the oldest lot is < 1 year old, reasons MUST warn about
  short-term capital gains tax. ✅T
- Purchase price MUST NOT influence the action (it is deliberately not an input to `stock_recommendation`).

## Limitations
Dividends, splits entered as lots, corporate actions, brokerage and tax are not modelled. Partial sales are not
tracked (delete or edit lots instead).
