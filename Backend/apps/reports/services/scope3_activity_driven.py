"""
apps/reports/services/scope3_activity_driven.py
================================================
Formula 1 + Formula 3 — Activity-Driven Projection for Scope 3 (Travel).

E_projected = Σ_{j=m+1}^{12} H_j × (1 + ΔD_j)

H_j = historical monthly emissions from prior FY same month
ΔD  = activity driver percentage change (provided by user via What-If UI)
"""

import math
import numpy as np
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime
from django.conf import settings as django_settings
from apps.emissions.models import TravelRow
from .utils import (
    fy_month_range, month_label, kg_to_tonnes,
    safe_float, confidence_from_cv,
)

_CI_Z = 1.645


def _travel_monthly(org, fy: str, month_number: int, segment_types: list) -> float:
    """Sum approved TravelRow co2e_kg for a given FY month, filtered by segment types."""
    start, end = fy_month_range(fy, month_number)
    fy_start_dt = timezone.make_aware(datetime(start.year, start.month, start.day))
    fy_end_dt   = timezone.make_aware(datetime(end.year, end.month, end.day, 23, 59, 59))

    qs = TravelRow.objects.filter(
        organisation=org,
        status='APPROVED',
    ).filter(
        Q(travel_date__range=(start, end)) |
        Q(check_in_date__range=(start, end))
    )
    if segment_types:
        qs = qs.filter(segment_type__in=segment_types)
    result = qs.aggregate(total=Sum('co2e_kg'))
    return kg_to_tonnes(result['total'])


def compute(org, fy: str, months_elapsed: int,
            activity_drivers: dict | None = None) -> list[dict]:
    """
    Compute Scope 3 activity-driven projection for remaining months.

    activity_drivers: {
        'air_travel':       float  (e.g. 0.10 = +10%, -0.05 = −5%)
        'hotel_stays':      float
        'ground_transport': float
    }
    """
    if months_elapsed == 0 or months_elapsed >= 12:
        return []

    drivers = activity_drivers or {}
    delta_air    = float(drivers.get('air_travel',       0.0))
    delta_hotel  = float(drivers.get('hotel_stays',      0.0))
    delta_ground = float(drivers.get('ground_transport', 0.0))

    prev_fy_start = int(fy.split('-')[0]) - 1
    prev_fy = f"{prev_fy_start}-{str(prev_fy_start + 1)[2:]}"

    # ── Build current-FY YTD monthly actuals (for σ calculation) ─────────────
    ytd_monthly = []
    for m in range(1, months_elapsed + 1):
        v = _travel_monthly(org, fy, m, [])
        ytd_monthly.append(v)

    # Monthly standard deviation from YTD actuals
    if len(ytd_monthly) >= 2:
        arr = np.array(ytd_monthly, dtype=float)
        sigma_monthly = float(np.std(arr, ddof=1))
        mean_monthly  = float(np.mean(arr))
        cv = sigma_monthly / mean_monthly if mean_monthly > 0 else 0.4
    else:
        sigma_monthly = (ytd_monthly[0] * 0.25) if ytd_monthly else 0.0
        cv = 0.4
    confidence = confidence_from_cv(cv)

    # ── Fallback monthly mean (when no prior-FY data) ─────────────────────────
    fallback_monthly = sum(ytd_monthly) / months_elapsed if months_elapsed > 0 else 0.0

    records = []
    for h, m in enumerate(range(months_elapsed + 1, 13), start=1):
        # H_j: historical baseline from prior FY same month (Formula 3)
        h_air    = _travel_monthly(org, prev_fy, m, ['AIR'])
        h_hotel  = _travel_monthly(org, prev_fy, m, ['HOTEL'])
        h_ground = _travel_monthly(org, prev_fy, m, ['CAR', 'RAIL', 'GROUND_TRANSPORT'])

        # If no prior-FY data for this segment, use equal portion of YTD mean
        if h_air + h_hotel + h_ground == 0:
            # Fall back to current YTD mean equally split across segments
            h_air    = fallback_monthly * 0.75   # air dominates Scope 3 travel
            h_hotel  = fallback_monthly * 0.20
            h_ground = fallback_monthly * 0.05

        # Apply activity drivers: E_projected = H_j × (1 + ΔD_j)
        e_air    = h_air    * (1 + delta_air)
        e_hotel  = h_hotel  * (1 + delta_hotel)
        e_ground = h_ground * (1 + delta_ground)
        e_total  = max(0.0, e_air + e_hotel + e_ground)

        # CI — grows with forecast horizon
        sigma_h = sigma_monthly * math.sqrt(h)
        lower   = max(0.0, e_total - _CI_Z * sigma_h)
        upper   = e_total + _CI_Z * sigma_h

        records.append({
            'month_number':        m,
            'month_label':         month_label(fy, m),
            'scope':               'SCOPE_3',
            'forecast_method':     'ACTIVITY_DRIVEN',
            'co2e_tonnes_central': round(e_total, 6),
            'co2e_tonnes_lower':   round(lower, 6),
            'co2e_tonnes_upper':   round(upper, 6),
            'confidence_pct':      confidence,
            'is_nowcast':          False,
            'rmsfe':               None,
            'activity_driver_air':    round(delta_air, 4),
            'activity_driver_hotel':  round(delta_hotel, 4),
            'activity_driver_ground': round(delta_ground, 4),
        })

    return records
