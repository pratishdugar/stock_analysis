"""Pure financial helpers: XIRR, CAGR, FD accrual, SIP schedules, currency conversion."""
import calendar
from datetime import date, timedelta

import pandas as pd

MIN_XIRR_DAYS = 90  # annualizing shorter periods is misleading


def cagr(start_value, end_value, years):
    if not start_value or start_value <= 0 or end_value is None or end_value < 0 or not years or years <= 0:
        return None
    return (end_value / start_value) ** (1 / years) - 1


def xirr(flows: list[tuple[date, float]]):
    """Annualized rate for dated cash flows (outflows negative). None if undefined or span too short."""
    flows = sorted(flows, key=lambda f: f[0])
    if len(flows) < 2 or not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    if (flows[-1][0] - flows[0][0]).days < MIN_XIRR_DAYS:
        return None
    d0 = flows[0][0]

    def npv(r):
        return sum(a / (1 + r) ** ((d - d0).days / 365.0) for d, a in flows)

    lo, hi = -0.99, 100.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def fd_value(principal, rate_pct, start: date, as_of: date, maturity: date | None = None, per_year: int = 4):
    """Estimated FD value with periodic compounding (default quarterly); stops accruing at maturity."""
    if principal is None or rate_pct is None or start is None:
        return None
    end = min(as_of, maturity) if maturity else as_of
    years = max((end - start).days, 0) / 365.0
    return principal * (1 + rate_pct / 100 / per_year) ** (per_year * years)


def sip_dates(start: date, end: date | None, day: int, as_of: date) -> list[date]:
    """Monthly instalment dates from `start` up to min(end, as_of); day clamped to month length."""
    last = min(end, as_of) if end else as_of
    out, y, m = [], start.year, start.month
    while (y, m) <= (last.year, last.month):
        d = date(y, m, min(max(int(day), 1), calendar.monthrange(y, m)[1]))
        if start <= d <= last:
            out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def nav_on_or_after(nav: pd.Series, d: date, max_gap_days: int = 7):
    """NAV on the first available date >= d (within max_gap_days), else None."""
    i = nav.index.searchsorted(pd.Timestamp(d))
    if i >= len(nav) or (nav.index[i].date() - d).days > max_gap_days:
        return None
    return float(nav.iloc[i])


def sip_position(amount: float, dates: list[date], nav: pd.Series) -> dict:
    """Units bought by a SIP at each instalment date's NAV. Instalments without a NAV are skipped."""
    units = invested = 0.0
    flows, skipped = [], 0
    for d in dates:
        n = nav_on_or_after(nav, d)
        if not n or n <= 0:
            skipped += 1
            continue
        units += amount / n
        invested += amount
        flows.append((d, -amount))
    return {"units": units, "invested": invested, "flows": flows, "skipped": skipped}


def convert(amount, from_ccy, to_ccy, usd_inr):
    """Convert between INR and USD only. None when a needed rate/currency is unavailable."""
    if amount is None:
        return None
    if from_ccy == to_ccy:
        return amount
    if not usd_inr or usd_inr <= 0:
        return None
    if (from_ccy, to_ccy) == ("USD", "INR"):
        return amount * usd_inr
    if (from_ccy, to_ccy) == ("INR", "USD"):
        return amount / usd_inr
    return None
