"""
apps/reports/views.py
=====================
BRSR (Business Responsibility & Sustainability Reporting) summary endpoint.
SEBI BRSR Core — Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 (12 July 2023)
+ December 2024 Industry Standards.

Covers all 4 environmental ESG attributes:
  1. GHG Emissions (Scope 1+2+3 + intensity)
  2-4: placeholders (Energy, Water, Waste)
"""

import logging
from datetime import date, datetime
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.emissions.models import SAPRow, UtilityRow, TravelRow
from apps.ingestion.models import EmissionFactor
from core.tenant import get_active_organisation

logger = logging.getLogger(__name__)


def _get_fy_dates(fy_str: str):
    """Parse 'YYYY-YY' into (start_date, end_date, start_dt, end_dt)."""
    start_year = int(fy_str.split('-')[0])
    fy_start = date(start_year, 4, 1)
    fy_end   = date(start_year + 1, 3, 31)
    # Timezone-aware datetimes for DateTimeField comparisons
    fy_start_dt = timezone.make_aware(datetime(start_year, 4, 1, 0, 0, 0))
    fy_end_dt   = timezone.make_aware(datetime(start_year + 1, 3, 31, 23, 59, 59))
    return fy_start, fy_end, fy_start_dt, fy_end_dt


def _current_fy() -> str:
    today = date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


def _prev_fy(fy_str: str) -> str:
    start_year = int(fy_str.split('-')[0])
    return f"{start_year - 1}-{str(start_year)[2:]}"


# Fuel key detection from esg_category string
FUEL_FACTOR_MAP = {
    'diesel':      {'unit': 'litres', 'factor': 2.6533},
    'petrol':      {'unit': 'litres', 'factor': 2.30},
    'cng':         {'unit': 'kg',     'factor': 2.21},
    'lpg':         {'unit': 'kg',     'factor': 2.983},
    'natural_gas': {'unit': 'm³',     'factor': 1.9141},
}


def _fuel_key_from_category(cat: str) -> str:
    cat_lower = (cat or '').lower()
    if 'diesel' in cat_lower:
        return 'diesel'
    elif 'petrol' in cat_lower:
        return 'petrol'
    elif 'cng' in cat_lower or 'compressed natural gas' in cat_lower:
        return 'cng'
    elif 'lpg' in cat_lower:
        return 'lpg'
    elif 'natural gas' in cat_lower:
        return 'natural_gas'
    return 'other'


def _compute_scope_data(org, fy_str):
    """
    Given an org and FY string, return the full scope data dict.
    Used for both current FY and previous FY.
    """
    fy_start, fy_end, fy_start_dt, fy_end_dt = _get_fy_dates(fy_str)

    # ── Scope 1 ───────────────────────────────────────────────────────────────
    sap_qs = SAPRow.objects.filter(
        organisation=org,
        document_date__range=(fy_start, fy_end),
    )
    scope1_approved = sap_qs.filter(status='APPROVED')
    scope1_total_kg = scope1_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0

    # By fuel type (for fuel consumption table)
    scope1_by_fuel = {}
    for row in scope1_approved.values('esg_category', 'unit_normalised').annotate(
        qty=Sum('quantity'), co2e=Sum('co2e_kg')
    ):
        fuel_key = _fuel_key_from_category(row['esg_category'] or '')
        info = FUEL_FACTOR_MAP.get(fuel_key, {
            'unit': row['unit_normalised'] or 'units', 'factor': None
        })
        if fuel_key not in scope1_by_fuel:
            scope1_by_fuel[fuel_key] = {
                'quantity':    0.0,
                'unit':        info['unit'],
                'co2e_tonnes': 0.0,
                'factor':      info.get('factor'),
            }
        scope1_by_fuel[fuel_key]['quantity']    += float(row['qty'] or 0)
        scope1_by_fuel[fuel_key]['co2e_tonnes'] += round(float(row['co2e'] or 0) / 1000, 6)

    scope1_ef = EmissionFactor.objects.filter(
        scope='SCOPE_1', is_active=True
    ).values('source_name').first()

    # ── Scope 2 ───────────────────────────────────────────────────────────────
    util_qs = UtilityRow.objects.filter(
        organisation=org,
        billing_start__range=(fy_start, fy_end),
    )
    scope2_approved = util_qs.filter(status='APPROVED')
    scope2_total_kg = scope2_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0
    scope2_kwh      = scope2_approved.aggregate(t=Sum('consumption_kwh'))['t'] or 0

    cea_factor = EmissionFactor.objects.filter(
        scope='SCOPE_2',
        fuel_or_activity_type='electricity_india',
        valid_from_fy__lte=fy_str,
    ).filter(
        Q(valid_to_fy__gte=fy_str) | Q(valid_to_fy__isnull=True)
    ).order_by('-valid_from_fy').first()

    # ── Scope 3 ───────────────────────────────────────────────────────────────
    travel_qs = TravelRow.objects.filter(
        Q(travel_date__range=(fy_start, fy_end)) |
        Q(check_in_date__range=(fy_start, fy_end)) |
        Q(car_pickup_datetime__range=(fy_start_dt, fy_end_dt)) |
        Q(created_at__range=(fy_start_dt, fy_end_dt),
          travel_date__isnull=True,
          check_in_date__isnull=True,
          car_pickup_datetime__isnull=True),
        organisation=org,
    )
    scope3_approved = travel_qs.filter(status='APPROVED')
    scope3_total_kg = scope3_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0

    scope3_by_cat = {
        'business_travel_air':    0.0,
        'business_travel_hotel':  0.0,
        'business_travel_ground': 0.0,
    }
    for row in scope3_approved.values('segment_type').annotate(total=Sum('co2e_kg')):
        seg   = (row['segment_type'] or '').upper()
        val_t = round(float(row['total'] or 0) / 1000, 6)
        if seg == 'AIR':
            scope3_by_cat['business_travel_air']    += val_t
        elif seg == 'HOTEL':
            scope3_by_cat['business_travel_hotel']  += val_t
        else:  # CAR, RAIL, GROUND_TRANSPORT, GROUND, UNKNOWN
            scope3_by_cat['business_travel_ground'] += val_t

    # ── Totals ────────────────────────────────────────────────────────────────
    s1_t = round(float(scope1_total_kg) / 1000, 6)
    s2_t = round(float(scope2_total_kg) / 1000, 6)
    s3_t = round(float(scope3_total_kg) / 1000, 6)

    return {
        'fy_str':          fy_str,
        's1_t':            s1_t,
        's2_t':            s2_t,
        's3_t':            s3_t,
        'sap_qs':          sap_qs,
        'scope1_approved': scope1_approved,
        'util_qs':         util_qs,
        'scope2_approved': scope2_approved,
        'travel_qs':       travel_qs,
        'scope3_approved': scope3_approved,
        'scope1_by_fuel':  scope1_by_fuel,
        'scope1_ef':       scope1_ef,
        'scope2_kwh':      float(scope2_kwh),
        'scope3_by_cat':   scope3_by_cat,
        'cea_factor':      cea_factor,
    }


class BRSRSummaryView(APIView):
    """
    GET /api/v1/reports/brsr-summary/?fy=2024-25

    Returns SEBI BRSR Core structured disclosure summary.
    Accessible by: Admin and Auditor roles only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_active_organisation(request)
        if org is None:
            return Response({'error': 'No active organisation.'}, status=403)

        # Role check
        from apps.organisations.models import OrganisationMembership
        try:
            membership = OrganisationMembership.objects.get(
                user=request.user, organisation=org
            )
            if membership.role not in ('ADMIN', 'AUDITOR', 'ANALYST'):
                return Response(
                    {'error': 'Only Admin, Analyst or Auditor roles can access BRSR reports.'},
                    status=403
                )
        except OrganisationMembership.DoesNotExist:
            return Response({'error': 'You are not a member of this organisation.'}, status=403)

        fy     = request.query_params.get('fy', _current_fy())
        pfy    = _prev_fy(fy)
        fy_start, fy_end, _s, _e = _get_fy_dates(fy)

        # ── Compute current FY data ───────────────────────────────────────────
        c = _compute_scope_data(org, fy)

        # ── Compute previous FY data ──────────────────────────────────────────
        p = _compute_scope_data(org, pfy)

        # ── Data quality ──────────────────────────────────────────────────────
        total_rows    = (c['sap_qs'].count() + c['util_qs'].count() + c['travel_qs'].count()) or 1
        approved_rows = (
            c['scope1_approved'].count() +
            c['scope2_approved'].count() +
            c['scope3_approved'].count()
        )
        completeness = round(approved_rows / total_rows * 100, 1)

        # Major variance: rows with co2_comparison_status flag OR anomaly_flags containing MAJOR_VARIANCE
        import json
        major_variance = (
            c['util_qs'].filter(co2_comparison_status='MAJOR_VARIANCE').count() +
            c['sap_qs'].filter(co2_comparison_status='MAJOR_VARIANCE').count()
        )
        # Also count rows flagged via anomaly_flags JSON array (for rows without doc comparison)
        for row in list(c['sap_qs'].values_list('anomaly_flags', flat=True)) + \
                    list(c['util_qs'].values_list('anomaly_flags', flat=True)):
            if row and 'MAJOR_VARIANCE' in (row if isinstance(row, list) else []):
                major_variance += 1
        pending_rows = (
            c['sap_qs'].filter(status='PENDING').count() +
            c['util_qs'].filter(status='PENDING').count() +
            c['travel_qs'].filter(status='PENDING').count()
        )

        from apps.ingestion.models import RowComment
        unresolved_findings = RowComment.objects.filter(
            organisation=org, is_finding=True, resolved=False,
        ).count()

        # ── Response ──────────────────────────────────────────────────────────
        cea  = c['cea_factor']

        return Response({
            # ─── Core identity ───────────────────────────────────────────────
            'reporting_period':   fy,
            'organisation':       org.name,
            'reporting_boundary': 'operational_control',
            'generated_at':       date.today().isoformat(),
            'generated_by':       request.user.email or request.user.username,

            # ─── Assurance (default, front-end can override) ──────────────────
            'assurance': {
                'level':    'none',
                'provider': None,
                'date':     None,
            },

            # ─── Scope 1 ────────────────────────────────────────────────────
            'scope_1': {
                'total_co2e_tonnes':      c['s1_t'],
                'by_fuel_type':           c['scope1_by_fuel'],
                'emission_factor_source': c['scope1_ef']['source_name'] if c['scope1_ef'] else 'IPCC_2006',
                'row_count':              c['sap_qs'].count(),
                'approved_row_count':     c['scope1_approved'].count(),
            },
            'scope_1_detail': {
                'by_fuel_type': c['scope1_by_fuel'],
                'by_gas_type': {
                    'co2': round(c['s1_t'], 6),  # All fuel combustion = CO2 (no CH4/N2O metered)
                    'ch4': 0.0,
                    'n2o': 0.0,
                },
            },

            # ─── Scope 2 ────────────────────────────────────────────────────
            'scope_2': {
                'total_co2e_tonnes':      c['s2_t'],
                'total_kwh_consumed':     round(c['scope2_kwh'], 2),
                'emission_factor_used':   cea.factor_value if cea else 0.710,
                'emission_factor_source': 'CEA_V20',
                'method':                 'location_based',
                'fy_factor_used':         cea.valid_from_fy if cea else fy,
                'row_count':              c['util_qs'].count(),
                'approved_row_count':     c['scope2_approved'].count(),
            },
            'scope_2_detail': {
                'total_kwh_consumed':     round(c['scope2_kwh'], 2),
                'renewable_kwh':          0.0,   # No RECs/PPAs — expand when available
                'emission_factor_used':   cea.factor_value if cea else 0.710,
                'emission_factor_source': 'CEA_V20',
                'fy_factor_used':         cea.valid_from_fy if cea else fy,
                'method':                 'location_based',
            },

            # ─── Scope 3 ────────────────────────────────────────────────────
            'scope_3': {
                'total_co2e_tonnes':  c['s3_t'],
                'by_category':        c['scope3_by_cat'],
                'row_count':          c['travel_qs'].count(),
                'approved_row_count': c['scope3_approved'].count(),
            },
            'scope_3_detail': {
                'comply_or_explain_status': 'disclosing',
                'explain_text':             None,
                'by_category':              c['scope3_by_cat'],
            },

            # ─── Totals ──────────────────────────────────────────────────────
            'total_co2e_tonnes': round(c['s1_t'] + c['s2_t'] + c['s3_t'], 6),

            # ─── Previous FY ─────────────────────────────────────────────────
            'previous_fy': {
                'reporting_period': pfy,
                'scope_1':  {'total_co2e_tonnes': p['s1_t']},
                'scope_2':  {'total_co2e_tonnes': p['s2_t']},
                'scope_3':  {'total_co2e_tonnes': p['s3_t']},
                'total_co2e_tonnes': round(p['s1_t'] + p['s2_t'] + p['s3_t'], 6),
            },

            # ─── Intensity (revenue comes from frontend localStorage) ─────────
            'intensity': {
                'revenue_inr_crore':      None,
                'scope_1_2_per_crore_inr': None,
                'scope_1_2_per_ppp_usd':  None,
            },

            # ─── Data quality ─────────────────────────────────────────────────
            'data_quality': {
                'rows_with_major_co2_variance':  major_variance,
                'rows_pending_approval':         pending_rows,
                'rows_with_unresolved_findings': unresolved_findings,
                'completeness_pct':              completeness,
            },
        })
