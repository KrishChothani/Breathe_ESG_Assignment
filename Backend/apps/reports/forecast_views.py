"""
apps/reports/forecast_views.py
================================
EmissionsForecastView — GET /api/v1/reports/emissions-forecast/
Blends YTD actuals + algorithmic projections into a 12-month timeline.
"""

import logging
from datetime import date
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.emissions.models import SAPRow, UtilityRow, TravelRow
from core.tenant import get_active_organisation
from .services.utils import current_fy_month, month_label as _mlabel, fy_month_range
from .services.forecast_router import compute_forecast

logger = logging.getLogger(__name__)


def _current_fy() -> str:
    today = date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


def _scope_data_for_fy(org, fy: str, months_elapsed: int):
    """Pull approved monthly actuals for each scope."""
    from datetime import datetime
    from django.utils import timezone

    monthly_actuals = {}
    for m in range(1, months_elapsed + 1):
        ms, me = fy_month_range(fy, m)

        s1_m = float(SAPRow.objects.filter(
            organisation=org, status='APPROVED',
            document_date__range=(ms, me),
        ).aggregate(t=Sum('co2e_kg'))['t'] or 0) / 1000

        s2_m = float(UtilityRow.objects.filter(
            organisation=org, status='APPROVED',
            billing_start__range=(ms, me),
        ).aggregate(t=Sum('co2e_kg'))['t'] or 0) / 1000

        s3_m = float(TravelRow.objects.filter(
            organisation=org, status='APPROVED',
        ).filter(
            Q(travel_date__range=(ms, me)) | Q(check_in_date__range=(ms, me))
        ).aggregate(t=Sum('co2e_kg'))['t'] or 0) / 1000

        monthly_actuals[m] = {
            'scope_1': round(s1_m, 6),
            'scope_2': round(s2_m, 6),
            'scope_3': round(s3_m, 6),
            'total':   round(s1_m + s2_m + s3_m, 6),
        }

    s1_ytd = round(sum(v['scope_1'] for v in monthly_actuals.values()), 6)
    s2_ytd = round(sum(v['scope_2'] for v in monthly_actuals.values()), 6)
    s3_ytd = round(sum(v['scope_3'] for v in monthly_actuals.values()), 6)

    return monthly_actuals, s1_ytd, s2_ytd, s3_ytd


class EmissionsForecastView(APIView):
    """
    GET /api/v1/reports/emissions-forecast/

    Query params:
      fy            str   e.g. "2025-26" (defaults to current FY)
      driver_air    float Delta % for air travel (0 = no change)
      driver_hotel  float Delta % for hotel stays
      driver_ground float Delta % for ground transport
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import ForecastedEmissions

        org = get_active_organisation(request)
        if not org:
            return Response({'error': 'No active organisation'}, status=403)

        fy = request.query_params.get('fy', _current_fy())

        def _driver(key):
            try:
                return float(request.query_params.get(key, 0))
            except (ValueError, TypeError):
                return 0.0

        drivers = {
            'air_travel':       _driver('driver_air'),
            'hotel_stays':      _driver('driver_hotel'),
            'ground_transport': _driver('driver_ground'),
        }

        months_elapsed = current_fy_month(fy)

        if months_elapsed < 1:
            return Response({
                'reporting_period': fy,
                'months_elapsed': 0,
                'months_remaining': 12,
                'error': 'INSUFFICIENT_DATA',
                'message': 'Forecast requires at least 1 complete month of approved data.',
                'ytd_actuals': {
                    'scope_1': {'co2e_tonnes': 0},
                    'scope_2': {'co2e_tonnes': 0},
                    'scope_3': {'co2e_tonnes': 0},
                    'total':   {'co2e_tonnes': 0},
                },
                'ytg_forecast': {}, 'monthly_timeline': [],
                'annualized_run_rate': {}, 'nowcast_quality': {},
                'activity_drivers_applied': drivers,
            })

        # ── Check stored forecasts; regenerate if drivers changed ──────────────
        existing = list(ForecastedEmissions.objects.filter(
            organisation=org, financial_year=fy
        ))
        stored_drivers = {'air_travel': 0.0, 'hotel_stays': 0.0, 'ground_transport': 0.0}
        if existing:
            s3_sample = next((r for r in existing if r.scope == 'SCOPE_3'), None)
            if s3_sample:
                stored_drivers = {
                    'air_travel':       float(s3_sample.activity_driver_air),
                    'hotel_stays':      float(s3_sample.activity_driver_hotel),
                    'ground_transport': float(s3_sample.activity_driver_ground),
                }

        needs_regen = not existing or stored_drivers != drivers
        if needs_regen:
            result = compute_forecast(org, fy, drivers)
            forecast_records = result['records']
        else:
            forecast_records = existing

        # ── YTD actuals ────────────────────────────────────────────────────────
        monthly_actuals, s1_ytd, s2_ytd, s3_ytd = _scope_data_for_fy(
            org, fy, months_elapsed
        )
        total_ytd = round(s1_ytd + s2_ytd + s3_ytd, 6)

        # ── Forecast record lookup ─────────────────────────────────────────────
        fc = {}
        for rec in forecast_records:
            mn = rec.month_number if hasattr(rec, 'month_number') else rec.get('month_number')
            sc = rec.scope if hasattr(rec, 'scope') else rec.get('scope')
            fc[(mn, sc)] = rec

        def _fval(m, scope, field, default=None):
            r = fc.get((m, scope))
            if r is None:
                return default
            v = getattr(r, field, None)
            return float(v) if v is not None else default

        def _fstr(m, scope, field):
            r = fc.get((m, scope))
            return str(getattr(r, field, '') or '') if r else ''

        # ── Build 12-month timeline ────────────────────────────────────────────
        timeline = []
        for m in range(1, 13):
            ml = _mlabel(fy, m)
            if m <= months_elapsed:
                a = monthly_actuals.get(m, {})
                timeline.append({
                    'month': ml, 'month_number': m, 'is_actual': True,
                    'scope_1': a.get('scope_1', 0),
                    'scope_2': a.get('scope_2', 0),
                    'scope_3': a.get('scope_3', 0),
                    'total':   a.get('total', 0),
                    'scope_1_lower': None, 'scope_1_upper': None,
                    'scope_2_lower': None, 'scope_2_upper': None,
                    'scope_3_lower': None, 'scope_3_upper': None,
                    'forecast_method_s1': None, 'forecast_method_s2': None,
                    'forecast_method_s3': None,
                    'confidence_s1': None, 'confidence_s2': None, 'confidence_s3': None,
                })
            else:
                s1c = _fval(m, 'SCOPE_1', 'co2e_tonnes_central', 0)
                s2c = _fval(m, 'SCOPE_2', 'co2e_tonnes_central', 0)
                s3c = _fval(m, 'SCOPE_3', 'co2e_tonnes_central', 0)
                timeline.append({
                    'month': ml, 'month_number': m, 'is_actual': False,
                    'scope_1': s1c, 'scope_2': s2c, 'scope_3': s3c,
                    'total': round(s1c + s2c + s3c, 6),
                    'scope_1_lower': _fval(m, 'SCOPE_1', 'co2e_tonnes_lower'),
                    'scope_1_upper': _fval(m, 'SCOPE_1', 'co2e_tonnes_upper'),
                    'scope_2_lower': _fval(m, 'SCOPE_2', 'co2e_tonnes_lower'),
                    'scope_2_upper': _fval(m, 'SCOPE_2', 'co2e_tonnes_upper'),
                    'scope_3_lower': _fval(m, 'SCOPE_3', 'co2e_tonnes_lower'),
                    'scope_3_upper': _fval(m, 'SCOPE_3', 'co2e_tonnes_upper'),
                    'forecast_method_s1': _fstr(m, 'SCOPE_1', 'forecast_method'),
                    'forecast_method_s2': _fstr(m, 'SCOPE_2', 'forecast_method'),
                    'forecast_method_s3': _fstr(m, 'SCOPE_3', 'forecast_method'),
                    'confidence_s1': _fval(m, 'SCOPE_1', 'confidence_pct'),
                    'confidence_s2': _fval(m, 'SCOPE_2', 'confidence_pct'),
                    'confidence_s3': _fval(m, 'SCOPE_3', 'confidence_pct'),
                })

        # ── YTG aggregates ─────────────────────────────────────────────────────
        future = list(range(months_elapsed + 1, 13))

        def _sum(scope, field):
            return round(sum(_fval(m, scope, field, 0) for m in future), 6)

        def _avg_conf(scope):
            vals = [_fval(m, scope, 'confidence_pct', 0) for m in future]
            return round(sum(vals) / len(vals)) if vals else 0

        def _method(scope):
            m0 = months_elapsed + 1
            return _fstr(m0, scope, 'forecast_method') if m0 <= 12 else ''

        def _arr(ytd):
            return round((ytd * 12) / months_elapsed, 6) if months_elapsed > 0 else 0.0

        s1_ytg = _sum('SCOPE_1', 'co2e_tonnes_central')
        s2_ytg = _sum('SCOPE_2', 'co2e_tonnes_central')
        s3_ytg = _sum('SCOPE_3', 'co2e_tonnes_central')

        rmsfe_s2 = next(
            (float(r.rmsfe) for r in forecast_records
             if hasattr(r, 'rmsfe') and r.rmsfe is not None),
            None
        )

        return Response({
            'reporting_period': fy,
            'generated_at':     date.today().isoformat(),
            'months_elapsed':   months_elapsed,
            'months_remaining': 12 - months_elapsed,

            'ytd_actuals': {
                'scope_1': {'co2e_tonnes': s1_ytd, 'months': months_elapsed},
                'scope_2': {'co2e_tonnes': s2_ytd, 'months': months_elapsed},
                'scope_3': {'co2e_tonnes': s3_ytd, 'months': months_elapsed},
                'total':   {'co2e_tonnes': total_ytd},
            },

            'ytg_forecast': {
                'scope_1': {
                    'co2e_tonnes': s1_ytg,
                    'lower': _sum('SCOPE_1', 'co2e_tonnes_lower'),
                    'upper': _sum('SCOPE_1', 'co2e_tonnes_upper'),
                    'method': _method('SCOPE_1'),
                    'confidence_pct': _avg_conf('SCOPE_1'),
                },
                'scope_2': {
                    'co2e_tonnes': s2_ytg,
                    'lower': _sum('SCOPE_2', 'co2e_tonnes_lower'),
                    'upper': _sum('SCOPE_2', 'co2e_tonnes_upper'),
                    'method': _method('SCOPE_2'),
                    'confidence_pct': _avg_conf('SCOPE_2'),
                },
                'scope_3': {
                    'co2e_tonnes': s3_ytg,
                    'lower': _sum('SCOPE_3', 'co2e_tonnes_lower'),
                    'upper': _sum('SCOPE_3', 'co2e_tonnes_upper'),
                    'method': _method('SCOPE_3'),
                    'confidence_pct': _avg_conf('SCOPE_3'),
                },
                'total': {
                    'co2e_tonnes': round(s1_ytg + s2_ytg + s3_ytg, 6),
                    'lower': round(
                        _sum('SCOPE_1', 'co2e_tonnes_lower') +
                        _sum('SCOPE_2', 'co2e_tonnes_lower') +
                        _sum('SCOPE_3', 'co2e_tonnes_lower'), 6
                    ),
                    'upper': round(
                        _sum('SCOPE_1', 'co2e_tonnes_upper') +
                        _sum('SCOPE_2', 'co2e_tonnes_upper') +
                        _sum('SCOPE_3', 'co2e_tonnes_upper'), 6
                    ),
                },
            },

            'annualized_run_rate': {
                'scope_1': _arr(s1_ytd),
                'scope_2': _arr(s2_ytd),
                'scope_3': _arr(s3_ytd),
                'total':   _arr(total_ytd),
            },

            'monthly_timeline': timeline,
            'nowcast_quality':  {'rmsfe_scope2': rmsfe_s2},
            'activity_drivers_applied': drivers,
        })
