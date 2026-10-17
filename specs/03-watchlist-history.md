# 03 · Watchlist and research history

## Intent
Remember which stocks the user follows and how their assessment changed over time.

## Requirements
- Users MUST be able to add the analysed ticker to a watchlist and remove selected tickers. ✅T
- Each analysis MUST save one snapshot per symbol per day (quant score, coverage, label, news score, combined
  score, currency, risk flags). A later save the same day updates the row but MUST keep a news/combined score
  already stored if the new save has none. ✅T
- The Analyse page SHOULD show up to 10 previous snapshots.
- The Watchlist view MUST compare up to 6 selected stocks (market, currency, quant score, coverage, 1y return,
  3y drawdown, label) and chart prices rebased to 100 over ~2 years (rebasing avoids FX conversion). A ticker that
  fails to load shows an error row instead of breaking the page. ✅T
