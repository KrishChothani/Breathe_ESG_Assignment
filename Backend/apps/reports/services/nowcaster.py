"""
apps/reports/services/nowcaster.py
===================================
Formula 6 — Nowcasting for data-lagged Scope 2 utility months.

Utility billing data typically lags 30-60 days. This module estimates
missing recent months using AR(1) + seasonal proxy from prior FY.

Panel equation (simplified for single-site operation):
  e_{i,t} = θ_i + ρ·e_{i,t−12} + ε_{i,t}

Where:
  θ_i = facility baseline (mean monthly kWh → tCO₂e)
  ρ   = AR(1) seasonal persistence coefficient (FORECAST_NOWCAST_AR_ALPHA)
  e_{i,t-12} = same calendar month from prior FY (strongest seasonal proxy)
"""

import math
import numpy as np
from datetime import date
from django.db.models import Sum, Avg
from django.conf import settings as django_settings
from apps.emissions.models import UtilityRow
from apps.ingestion.models import EmissionFactor
from .utils import fy_month_range, kg_to_tonnes, safe_float


# AR(1) coefficient: how much of the prior-year same-month value carries forward
AR_ALPHA = getattr(django_settings, 'FORECAST_NOWCAST_AR_ALPHA', 0.65)

# Grid emission factor fallback (CEA V20 FY 2024-25)
_FALLBACK_GRID_FACTOR = 0.710   # kgCO₂e / kWh


def _grid_factor_for_fy(fy: str) -> float:
    """Fetch CEA grid factor for the given FY from EmissionFactor table."""
    ef = EmissionFactor.objects.filter(
        scope='SCOPE_2',
        fuel_or_activity_type='electricity_india',
        is_active=True,
    ).order_by('-valid_from_fy').first()
    if ef:
        return float(ef.factor_value)
    return _FALLBACK_GRID_FACTOR


def estimate_missing_months(org, fy: str, months_elapsed: int, known_monthly_co2: dict) -> dict:
    """
    For each FY month index NOT in known_monthly_co2, estimate tCO₂e via nowcasting.

    known_monthly_co2: {month_number: float(tCO₂e)} — from actual UtilityRow records
    Returns: {month_number: {'value': float, 'is_nowcast': bool, 'rmsfe': float}}
    """
    prev_fy_start_year = int(fy.split('-')[0]) - 1
    prev_fy = f"{prev_fy_start_year}-{str(prev_fy_start_year + 1)[2:]}"
    grid_factor = _grid_factor_for_fy(fy)

    # Gather all facility site names to compute facility-level baselines
    facilities = list(
        UtilityRow.objects.filter(organisation=org, status='APPROVED')
        .values_list('site_name', flat=True)
        .distinct()
    )

    result = {}
    rmsfe_accumulator = []

    for m in range(1, months_elapsed + 1):
        if m in known_monthly_co2:
            result[m] = {'value': known_monthly_co2[m], 'is_nowcast': False, 'rmsfe': None}
            continue

        # ── Nowcast this month using prior FY same calendar month ─────────────
        start, end = fy_month_range(fy, m)
        prev_start, prev_end = fy_month_range(prev_fy, m)

        # Prior-FY same month actual (seasonal anchor e_{i,t-12})
        prior_result = UtilityRow.objects.filter(
            organisation=org,
            billing_start__range=(prev_start, prev_end),
            status='APPROVED',
        ).aggregate(total_kwh=Sum('consumption_kwh'), total_co2=Sum('co2e_kg'))

        prior_co2_t = kg_to_tonnes(prior_result['total_co2'])

        # Facility-level mean baseline (θ_i component)
        baseline_result = UtilityRow.objects.filter(
            organisation=org,
            status='APPROVED',
        ).aggregate(mean_co2=Avg('co2e_kg'))
        facility_mean_t = kg_to_tonnes(baseline_result['mean_co2'] or 0) * len(facilities)

        # AR(1) nowcast: e_t = α·e_{t-12} + (1-α)·θ
        if prior_co2_t > 0:
            nowcast_t = AR_ALPHA * prior_co2_t + (1 - AR_ALPHA) * facility_mean_t
        else:
            # No prior-year data: fall back to facility mean
            nowcast_t = facility_mean_t

        # Back-test RMSFE: compare nowcast of the LAST known month vs its actual
        # (Simplified: use the most recent known month as validation point)
        if known_monthly_co2:
            last_known_m = max(known_monthly_co2.keys())
            actual_val   = known_monthly_co2[last_known_m]
            lk_prev_start, lk_prev_end = fy_month_range(prev_fy, last_known_m)
            lk_prior = UtilityRow.objects.filter(
                organisation=org,
                billing_start__range=(lk_prev_start, lk_prev_end),
                status='APPROVED',
            ).aggregate(total=Sum('co2e_kg'))
            lk_prior_t = kg_to_tonnes(lk_prior['total'])
            lk_mean_t  = facility_mean_t
            backtest_nowcast = AR_ALPHA * lk_prior_t + (1 - AR_ALPHA) * lk_mean_t
            error = (backtest_nowcast - actual_val) ** 2
            rmsfe_accumulator.append(error)

        result[m] = {
            'value':      round(nowcast_t, 6),
            'is_nowcast': True,
            'rmsfe':      None,  # filled below
        }

    # Compute RMSFE across all nowcast validation points
    rmsfe = None
    if rmsfe_accumulator:
        rmsfe = round(math.sqrt(sum(rmsfe_accumulator) / len(rmsfe_accumulator)), 6)
        for m_num in result:
            if result[m_num]['is_nowcast']:
                result[m_num]['rmsfe'] = rmsfe

    return result, rmsfe
