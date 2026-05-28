"""
apps/reports/services/forecast_router.py
=========================================
Entry point for all forecast computation.
Routes each scope to the appropriate engine and persists results.
"""

import logging
from django.db import transaction
from apps.reports.models import ForecastedEmissions
from .utils import current_fy_month
from . import scope1_run_rate, scope2_ets, scope3_activity_driven

logger = logging.getLogger(__name__)


def compute_forecast(org, fy: str, activity_drivers: dict | None = None) -> dict:
    """
    Orchestrates forecast for all three scopes for a given org + FY.

    Steps:
      1. Determine months elapsed in the FY
      2. Route to each scope engine
      3. Persist ForecastedEmissions records (replace any existing)
      4. Return structured result dict (mirrors API response shape)

    Returns: {
        'months_elapsed': int,
        'months_remaining': int,
        'records': list[ForecastedEmissions],
        'nowcast_quality': dict,
    }
    """
    months_elapsed = current_fy_month(fy)
    drivers = activity_drivers or {}

    logger.info(
        "Generating forecast for org=%s fy=%s months_elapsed=%d drivers=%s",
        org.slug, fy, months_elapsed, drivers
    )

    if months_elapsed < 1:
        logger.warning("Forecast skipped: no complete months elapsed in FY %s", fy)
        return {
            'months_elapsed': 0,
            'months_remaining': 12,
            'records': [],
            'nowcast_quality': {},
            'error': 'INSUFFICIENT_DATA',
        }

    # ── Run scope engines ──────────────────────────────────────────────────────
    try:
        s1_records = scope1_run_rate.compute(org, fy, months_elapsed)
    except Exception as e:
        logger.error("Scope 1 forecast failed: %s", e)
        s1_records = []

    try:
        s2_records = scope2_ets.compute(org, fy, months_elapsed)
    except Exception as e:
        logger.error("Scope 2 ETS forecast failed: %s", e)
        s2_records = []

    try:
        s3_records = scope3_activity_driven.compute(org, fy, months_elapsed, drivers)
    except Exception as e:
        logger.error("Scope 3 forecast failed: %s", e)
        s3_records = []

    all_dicts = s1_records + s2_records + s3_records

    # ── Persist (atomic replace) ───────────────────────────────────────────────
    db_records = []
    with transaction.atomic():
        ForecastedEmissions.objects.filter(
            organisation=org,
            financial_year=fy,
        ).delete()

        for d in all_dicts:
            fe = ForecastedEmissions(
                organisation            = org,
                financial_year          = fy,
                month_number            = d['month_number'],
                month_label             = d['month_label'],
                scope                   = d['scope'],
                forecast_method         = d['forecast_method'],
                co2e_tonnes_central     = d['co2e_tonnes_central'],
                co2e_tonnes_lower       = d.get('co2e_tonnes_lower'),
                co2e_tonnes_upper       = d.get('co2e_tonnes_upper'),
                confidence_pct          = d.get('confidence_pct', 0),
                is_nowcast              = d.get('is_nowcast', False),
                rmsfe                   = d.get('rmsfe'),
                activity_driver_air     = d.get('activity_driver_air', 0),
                activity_driver_hotel   = d.get('activity_driver_hotel', 0),
                activity_driver_ground  = d.get('activity_driver_ground', 0),
                generated_by_task       = 'inline',
            )
            db_records.append(fe)

        ForecastedEmissions.objects.bulk_create(db_records)

    # Nowcast quality summary (from Scope 2 records)
    s2_nowcast_rmsfe = next(
        (r.get('rmsfe') for r in s2_records if r.get('rmsfe') is not None), None
    )

    logger.info(
        "Forecast persisted: %d records for org=%s fy=%s",
        len(db_records), org.slug, fy
    )

    return {
        'months_elapsed':   months_elapsed,
        'months_remaining': 12 - months_elapsed,
        'records':          db_records,
        'nowcast_quality': {
            'rmsfe_scope2': s2_nowcast_rmsfe,
        },
    }
