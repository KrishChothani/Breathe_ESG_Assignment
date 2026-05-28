"""
apps/reports/services/scope2_ets.py
=====================================
Formulas 4 + 5 + 6 — Seasonal decomposition + Holt-Winters ETS for Scope 2.

Pipeline:
  1. Nowcasting (Formula 6)   — fill billing-lagged months with proxy estimates
  2. Decomposition (Formula 4) — Y_t = T_t + S_t + I_t
  3. ETS Forecast (Formula 5)  — Ŷ_{t+h} = L_{t-1} + h·B_t + SN_{t-h+1}

Pure numpy implementation; no external time-series library required.
"""

import math
import numpy as np
from django.db.models import Sum
from django.conf import settings as django_settings
from apps.emissions.models import UtilityRow
from apps.ingestion.models import EmissionFactor
from .utils import (
    fy_month_range, month_label, kg_to_tonnes,
    safe_float, confidence_from_cv,
)
from .nowcaster import estimate_missing_months

# ── ETS hyper-parameters (tunable via settings) ───────────────────────────────
_ALPHA = getattr(django_settings, 'FORECAST_ETS_ALPHA', 0.3)   # level smoothing
_BETA  = getattr(django_settings, 'FORECAST_ETS_BETA',  0.1)   # trend smoothing
_GAMMA = getattr(django_settings, 'FORECAST_ETS_GAMMA', 0.6)   # seasonal smoothing
_SEAS  = 12                                                      # seasonal period
_CI_Z  = 1.645                                                   # 90% confidence


def _build_time_series(org, fy: str, months_elapsed: int) -> tuple[list, dict]:
    """
    Build a list of monthly tCO₂e values for months 1..months_elapsed.
    Gaps (billing-lagged months) are filled via the nowcaster.
    Returns (series_list, nowcast_metadata_dict).
    """
    # Gather known actual months
    known = {}
    for m in range(1, months_elapsed + 1):
        start, end = fy_month_range(fy, m)
        res = UtilityRow.objects.filter(
            organisation=org,
            billing_start__range=(start, end),
            status='APPROVED',
        ).aggregate(total=Sum('co2e_kg'))
        val = kg_to_tonnes(res['total'])
        if val > 0:
            known[m] = val

    filled, rmsfe = estimate_missing_months(org, fy, months_elapsed, known)

    series = []
    for m in range(1, months_elapsed + 1):
        entry = filled.get(m, {'value': 0.0, 'is_nowcast': False, 'rmsfe': None})
        series.append(entry['value'])

    return series, filled, rmsfe


def _additive_decompose(series: list) -> tuple[list, list]:
    """
    Formula 4: Additive decomposition Y_t = T_t + S_t + I_t
    Returns (trend, seasonal_factors) where seasonal_factors[0..11] are
    indexed by calendar position in the series.
    """
    n = len(series)
    arr = np.array(series, dtype=float)

    # Trend: centered moving average (window=3, or min of series length)
    window = min(3, n)
    if window >= 2:
        trend = np.convolve(arr, np.ones(window) / window, mode='same')
        # Edges correction — use nearest valid value
        half = window // 2
        for i in range(half):
            trend[i] = arr[:i + half + 1].mean()
        for i in range(n - half, n):
            trend[i] = arr[i - half:].mean()
    else:
        trend = arr.copy()

    # Seasonal: deviation from trend, averaged by position mod 12
    detrended = arr - trend
    seasonal_factors = np.zeros(12)
    counts = np.zeros(12)
    for i, v in enumerate(detrended):
        idx = i % 12
        seasonal_factors[idx] += v
        counts[idx] += 1
    with np.errstate(invalid='ignore'):
        seasonal_factors = np.where(counts > 0, seasonal_factors / counts, 0.0)

    # Normalize so seasonal factors sum to 0 (additive constraint)
    seasonal_factors -= seasonal_factors.mean()

    return trend.tolist(), seasonal_factors.tolist()


def _holt_winters_forecast(series: list, seasonal_factors: list,
                            horizon: int) -> tuple[list, float]:
    """
    Formula 5: Additive Holt-Winters ETS forecast.
    Ŷ_{t+h} = L_{t-1} + h·B_t + SN_{t-h+1}

    Returns (forecasts_list, sigma_one_step).
    """
    n = len(series)
    arr = np.array(series, dtype=float)
    sf  = np.array(seasonal_factors, dtype=float)

    if n < 2:
        # Degenerate: just repeat last value
        forecasts = [float(arr[-1])] * horizon if n > 0 else [0.0] * horizon
        return forecasts, 0.0

    # Initialise state
    L = arr[0] - sf[0]          # level
    B = (arr[1] - arr[0]) / 2   # trend (rough)
    SN = sf.copy()               # seasonal offsets

    errors = []
    for t in range(n):
        s_idx = t % _SEAS
        # One-step-ahead forecast
        y_hat = L + B + SN[s_idx]
        err   = arr[t] - y_hat
        errors.append(err)

        # Update state (Holt-Winters additive)
        L_new = _ALPHA * (arr[t] - SN[s_idx]) + (1 - _ALPHA) * (L + B)
        B_new = _BETA  * (L_new - L)           + (1 - _BETA)  * B
        SN[s_idx] = _GAMMA * (arr[t] - L_new)  + (1 - _GAMMA) * SN[s_idx]
        L, B = L_new, B_new

    # RMSE of in-sample one-step errors (used for CI)
    sigma_one_step = float(np.sqrt(np.mean(np.array(errors) ** 2))) if errors else 0.0

    # Forecast h steps ahead
    forecasts = []
    for h in range(1, horizon + 1):
        s_idx = (n + h - 1) % _SEAS
        y_hat_h = max(0.0, L + h * B + SN[s_idx])
        forecasts.append(float(y_hat_h))

    return forecasts, sigma_one_step


def compute(org, fy: str, months_elapsed: int) -> list[dict]:
    """
    Compute Scope 2 ETS forecast for remaining months.
    Returns list of forecast dicts (same schema as scope1_run_rate).
    """
    if months_elapsed == 0 or months_elapsed >= 12:
        return []

    series, filled_meta, rmsfe = _build_time_series(org, fy, months_elapsed)
    remaining_months = 12 - months_elapsed

    if not series or sum(series) == 0:
        # No utility data at all — return zero forecasts flagged as INSUFFICIENT
        records = []
        for m in range(months_elapsed + 1, 13):
            records.append({
                'month_number': m, 'month_label': month_label(fy, m),
                'scope': 'SCOPE_2', 'forecast_method': 'INSUFFICIENT',
                'co2e_tonnes_central': 0.0, 'co2e_tonnes_lower': 0.0,
                'co2e_tonnes_upper': 0.0, 'confidence_pct': 0,
                'is_nowcast': False, 'rmsfe': None,
                'activity_driver_air': 0, 'activity_driver_hotel': 0,
                'activity_driver_ground': 0,
            })
        return records

    # Seasonal decomposition (Formula 4)
    trend, seasonal_factors = _additive_decompose(series)

    # ETS forecast (Formula 5)
    forecasts, sigma_one_step = _holt_winters_forecast(
        series, seasonal_factors, remaining_months
    )

    # Confidence derivation
    mean_forecast = float(np.mean(forecasts)) if forecasts else 1.0
    cv = sigma_one_step / mean_forecast if mean_forecast > 0 else 0.3
    confidence = confidence_from_cv(cv)

    records = []
    for h, (m, f_val) in enumerate(
        zip(range(months_elapsed + 1, 13), forecasts), start=1
    ):
        # CI grows with horizon (σ_h = σ · √h)
        sigma_h = sigma_one_step * math.sqrt(h)
        lower = max(0.0, f_val - _CI_Z * sigma_h)
        upper = f_val + _CI_Z * sigma_h

        records.append({
            'month_number':        m,
            'month_label':         month_label(fy, m),
            'scope':               'SCOPE_2',
            'forecast_method':     'ETS',
            'co2e_tonnes_central': round(f_val, 6),
            'co2e_tonnes_lower':   round(lower, 6),
            'co2e_tonnes_upper':   round(upper, 6),
            'confidence_pct':      confidence,
            'is_nowcast':          False,
            'rmsfe':               rmsfe,
            'activity_driver_air':    0,
            'activity_driver_hotel':  0,
            'activity_driver_ground': 0,
        })

    return records
