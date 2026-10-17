# 06 · Portfolio — mutual funds and SIPs

## Intent
Track mutual fund holdings and running SIPs, value them from published NAVs and judge each fund over the
long-term window.

## Data entry
- Funds: Indian funds by AMFI scheme code via the free `api.mfapi.in` (with name search), or any fund with a Yahoo
  ticker. Category (Equity / Hybrid / Debt / Other), benchmark Yahoo symbol (default `^NSEI`, blank for none),
  optional expense ratio. A fund is saved only if its NAV history loads. Deleting a fund deletes its lots and SIPs. ✅T
- Lump-sum purchases: units, NAV, date.
- SIPs: monthly amount, day of month (1–31, clamped to month length), start date, optional end date. SIP
  instalments MUST NOT also be entered as lump sums.

## Valuation
- SIP units = Σ amount ÷ NAV on the first NAV date on/after each instalment date (skipped, with a warning, if no NAV
  within 7 days). ✅T
- Fund value = (lump-sum units + SIP units) × latest NAV; P&L and XIRR from all cash flows. ✅T
- Overview MUST list every SIP with amount, day, start/end, status (Active/Ended), invested, value and the fund's
  recommendation, plus the total active monthly SIP amount. ✅T
- Yahoo-sourced funds use unadjusted prices so historical units are bought at the real price.

## Fund score and recommendation (src/mutual_funds.py `analyse_fund`)
- Window = 5 years if ≥ 5 years of NAV history and horizon ≥ 5, else 3 years; < 3 years → "Not enough history –
  cannot assess". ✅T
- Score 0–100 = return 50% + risk-adjusted 25% + drawdown 25%:
  return = excess CAGR vs benchmark −3%→+3%/yr (equity/hybrid with benchmark data); debt: CAGR vs the hurdle
  (`risk_free_pct` − 2% → + 1%); no benchmark: CAGR vs hurdle → hurdle + 8%. Risk-adjusted = (CAGR − hurdle) ÷
  volatility, 0 → 0.7. Drawdown: equity −45% → −15%; debt/hybrid −20% → −2%. ✅T
- Risks: expense ratio > 1.5% (equity) / > 1.0% (debt); drawdown worse than −40% (non-debt).
- Action: score ≥ `fund_buy_min` (65) and no risks → **Continue SIP / add more**; ≥ `fund_hold_min` (45) →
  **Hold / continue**; else **Review fund (compare with category peers)**. ✅T

## Limitations
No category-peer ranking, rolling returns, manager or portfolio data. mfapi.in is a free community API (not
official AMFI) and may change. Stamp duty, missed instalments, exit loads and taxes are ignored.
