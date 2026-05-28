"""
apps/reports/services/scope1_run_rate.py
========================================
Formula 1 (GHG Baseline) + Formula 2 (Annualized Run Rate)

Scope 1 fuel procurement data (SAPRow) is relatively flat and
procurement-driven. Simple run-rate extrapolation is statistically
appropriate and auditor-friendly.

GHG = Σ(Activity × EmissionFactor)  — pre-computed per row as co2e_kg
Run Rate = (Emissions_YTD × 12) / M
"""

import math
import numpy as np
from django.db.models import Sum
from apps.emissions.models import SAPRow
from .utils import (
    fy_month_range, month_label, kg_to_tonnes,
    safe_float, confidence_from_cv,
)


def compute(org, fy: str, months_elapsed: int, settings=None) -> list[dict]:
    """
    Compute Scope 1 run-rate forecast for remaining months.

    Returns a list of dicts, one per remaining FY month:
    {
        month_number: int,
        month_label: str,
        scope: 'SCOPE_1',
        forecast_method: 'RUN_RATE',
        co2e_tonnes_central: float,
        co2e_tonnes_lower: float,
        co2e_tonnes_upper: float,
        confidence_pct: int,
        is_nowcast: False,
        rmsfe: None,
    }
    """
    if months_elapsed == 0 or months_elapsed >= 12:
        return []

    # ── Step 1: Gather monthly YTD actuals (Formula 1 satisfied per row) ──────
    monthly_actuals = []
    for m in range(1, months_elapsed + 1):
        start, end = fy_month_range(fy, m)
        result = SAPRow.objects.filter(
            organisation=org,
            document_date__range=(start, end),
            status='APPROVED',
        ).aggregate(total=Sum('co2e_kg'))
        monthly_actuals.append(kg_to_tonnes(result['total']))

    ytd_total = sum(monthly_actuals)

    # ── Step 2: Run Rate extrapolation (Formula 2) ────────────────────────────
    # Run Rate = (Emissions_YTD × 12) / M
    annualized = (ytd_total * 12) / months_elapsed
    remaining_months = 12 - months_elapsed

    # Monthly average for remaining period
    monthly_forecast = annualized / 12

    # ── Step 3: Confidence intervals using monthly variance ───────────────────
    if len(monthly_actuals) >= 2:
        arr = np.array(monthly_actuals, dtype=float)
        sigma_monthly = float(np.std(arr, ddof=1))
        mean_monthly  = float(np.mean(arr))
        cv = sigma_monthly / mean_monthly if mean_monthly > 0 else 0.5
    else:
        # Single month: use 20% CV as conservative prior
        sigma_monthly = monthly_forecast * 0.20
        cv = 0.20

    # 90% CI: z=1.645; error grows with √h (horizon)
    CI_Z = 1.645
    confidence = confidence_from_cv(cv)

    records = []
    for h, m in enumerate(range(months_elapsed + 1, 13), start=1):
        sigma_h = sigma_monthly * math.sqrt(h)
        lower = max(0.0, monthly_forecast - CI_Z * sigma_h)
        upper = monthly_forecast + CI_Z * sigma_h

        records.append({
            'month_number':        m,
            'month_label':         month_label(fy, m),
            'scope':               'SCOPE_1',
            'forecast_method':     'RUN_RATE',
            'co2e_tonnes_central': round(monthly_forecast, 6),
            'co2e_tonnes_lower':   round(lower, 6),
            'co2e_tonnes_upper':   round(upper, 6),
            'confidence_pct':      confidence,
            'is_nowcast':          False,
            'rmsfe':               None,
            'activity_driver_air':    0,
            'activity_driver_hotel':  0,
            'activity_driver_ground': 0,
        })

    return records
