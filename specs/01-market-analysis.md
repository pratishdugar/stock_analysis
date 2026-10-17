# 01 · Market analysis and quantitative score

## Intent
Turn a ticker into an explainable 0–100 quality/value/momentum score plus charts, without pretending to more
precision than the free data supports.

## Requirements
- MUST accept US (`AAPL`), NSE (`TCS.NS`) and BSE (`TCS.BO`) tickers; normalise case/whitespace and reject malformed
  input with a helpful message. ✅T
- MUST fetch ~5 years of daily adjusted prices and Yahoo `info` fundamentals; any failure (network, rate limit,
  unknown ticker, < 2 rows) becomes a readable error, never a crash. ✅T
- MUST show price (with SMA 50/200), volume, 1m/3m/6m/1y/3y returns, 1y return vs benchmark, 3y max drawdown,
  annualised volatility and RSI(14). Benchmarks: S&P 500 (`^GSPC`) for US, Nifty 50 (`^NSEI`) for `.NS`,
  Sensex (`^BSESN`) for `.BO`.
- MUST show the price currency, the financial-statement currency and the last data date.

## Score (src/scoring.py)
Five components, each the average of its available sub-metrics (each mapped linearly to 0..1), scaled to its max:

| Component (max) | Sub-metrics: value giving 0 → value giving full marks |
|---|---|
| Quality (20) | ROE 5%→25%; profit margin 3%→25%; operating margin 5%→30% (skipped for Financial Services) |
| Growth (15) | revenue growth 0%→20%; earnings growth 0%→25% |
| Valuation (15) | trailing and forward P/E: 45→15 (P/E ≤ 0 scores 0) |
| Financial health (10) | debt/equity 250%→50%; current ratio 0.8→2.0; free cash flow > 0 (all skipped for financials) |
| Momentum (10) | 1y return −10%→+30%; 3y max drawdown −60%→−15%; above 200-day MA; 1y vs benchmark −10%→+10% |

- Score = points earned ÷ max points of *available* components × 100. If available components cover < 60% of the
  70 points, the score is **Incomplete** (no number, no label). ✅T
- Risk flags: trailing P/E > 60; negative profit margin; debt/equity > 300% or negative FCF (non-financials);
  3y drawdown worse than −60%; incomplete data. Any flag blocks *Buy Candidate*. ✅T
- Labels: ≥ 75 Buy Candidate · 55–74.9 Hold / Watchlist · < 55 Avoid / Sell-Review. ✅T

## Limitations
Thresholds are generic (not calibrated per sector or country). Yahoo data is unofficial and may be stale or wrong;
field names/units (e.g. debt/equity in percent) can change. Returns use trading-day counts (252/year).
