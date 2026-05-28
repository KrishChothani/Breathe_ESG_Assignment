"""
apps/reports/services/utils.py
==============================
Shared helpers for all forecasting engines.
"""

from datetime import date
from decimal import Decimal


# India FY: month 1 = April, month 12 = March
_MONTH_MAP = {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9,
              7: 10, 8: 11, 9: 12, 10: 1, 11: 2, 12: 3}


def fy_month_range(fy_str: str, month_number: int):
    """
    Return (start_date, end_date) for a given India FY month number.
    month_number: 1=Apr, 2=May, … 12=Mar
    """
    start_year = int(fy_str.split('-')[0])
    cal_month = _MONTH_MAP[month_number]
    if cal_month >= 4:
        year = start_year
    else:
        year = start_year + 1
    from calendar import monthrange
    _, last_day = monthrange(year, cal_month)
    return date(year, cal_month, 1), date(year, cal_month, last_day)


def month_label(fy_str: str, month_number: int) -> str:
    """Return ISO month string e.g. '2025-09'."""
    start_year = int(fy_str.split('-')[0])
    cal_month = _MONTH_MAP[month_number]
    year = start_year if cal_month >= 4 else start_year + 1
    return f"{year}-{cal_month:02d}"


def current_fy_month(fy_str: str) -> int:
    """
    Return how many complete India FY months have elapsed in fy_str up to today.
    Returns 0 if no months have completed yet (we're before end of month 1).
    Returns 12 if the FY is fully complete.
    """
    today = date.today()
    start_year = int(fy_str.split('-')[0])
    fy_start = date(start_year, 4, 1)
    fy_end   = date(start_year + 1, 3, 31)

    if today < fy_start:
        return 0
    if today > fy_end:
        return 12

    # Months elapsed = how many complete calendar months between Apr and today
    if today.month >= 4:
        months_elapsed = today.month - 4  # Apr=0 complete, May=1, ...
    else:
        months_elapsed = today.month + 8  # Jan=9, Feb=10, Mar=11

    # Only count months with a completed end date
    # e.g., on May 15 → April is complete (1 month), May is not yet complete (0)
    return max(0, months_elapsed)


def kg_to_tonnes(kg_value) -> float:
    """Convert kg CO₂e to metric tonnes."""
    return round(float(kg_value or 0) / 1000, 6)


def safe_float(v, default=0.0) -> float:
    """Safely cast Decimal/None to float."""
    if v is None:
        return default
    return float(v)


def confidence_from_cv(cv: float) -> int:
    """
    Map coefficient of variation (σ/μ) to a 0–100 confidence score.
    Lower CV → higher confidence.
    """
    if cv <= 0.05:
        return 95
    elif cv <= 0.10:
        return 90
    elif cv <= 0.20:
        return 82
    elif cv <= 0.30:
        return 74
    elif cv <= 0.50:
        return 62
    return 50
