"""
apps/reports/views.py
=====================
BRSR (Business Responsibility & Sustainability Reporting) summary endpoint.
Compliant with SEBI BRSR Core mandatory disclosure format for FY 2025-26+.
"""

import logging
from datetime import date
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.emissions.models import SAPRow, UtilityRow, TravelRow
from apps.ingestion.models import EmissionFactor
from core.tenant import get_active_organisation

logger = logging.getLogger(__name__)


def _get_fy_dates(fy_str: str):
    """Parse 'YYYY-YY' into (start_date, end_date)."""
    start_year = int(fy_str.split('-')[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def _current_fy() -> str:
    today = date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


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

        # Role check: only Admin and Auditor
        from apps.organisations.models import OrganisationMembership
        try:
            membership = OrganisationMembership.objects.get(
                user=request.user, organisation=org
            )
            if membership.role not in ('ADMIN', 'AUDITOR'):
                return Response(
                    {'error': 'Only Admin or Auditor roles can access BRSR reports.'},
                    status=403
                )
        except OrganisationMembership.DoesNotExist:
            return Response({'error': 'You are not a member of this organisation.'}, status=403)

        fy = request.query_params.get('fy', _current_fy())
        fy_start, fy_end = _get_fy_dates(fy)

        # ── Scope 1 — SAP fuel rows ──────────────────────────────────────────
        sap_qs = SAPRow.objects.filter(
            organisation=org,
            document_date__range=(fy_start, fy_end),
        )
        scope1_approved = sap_qs.filter(status='APPROVED')
        scope1_total_kg = scope1_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0

        # By fuel type (from ghg_category field)
        scope1_by_fuel = {}
        for row in scope1_approved.values('ghg_category').annotate(total=Sum('co2e_kg')):
            cat  = (row['ghg_category'] or 'Unknown').lower().replace('fuel combustion — ', '')
            scope1_by_fuel[cat] = round(float(row['total'] or 0) / 1000, 4)  # to tonnes

        scope1_ef = EmissionFactor.objects.filter(
            scope='SCOPE_1', is_active=True
        ).values('source_name').first()

        # ── Scope 2 — Utility electricity rows ───────────────────────────────
        util_qs = UtilityRow.objects.filter(
            organisation=org,
            billing_start__range=(fy_start, fy_end),
        )
        scope2_approved = util_qs.filter(status='APPROVED')
        scope2_total_kg = scope2_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0
        scope2_kwh      = scope2_approved.aggregate(t=Sum('consumption_kwh'))['t'] or 0

        # Get the CEA factor for this FY
        cea_factor = EmissionFactor.objects.filter(
            scope='SCOPE_2',
            fuel_or_activity_type='electricity_india',
            valid_from_fy__lte=fy,
        ).filter(
            Q(valid_to_fy__gte=fy) | Q(valid_to_fy__isnull=True)
        ).order_by('-valid_from_fy').first()

        # ── Scope 3 — Travel rows ─────────────────────────────────────────────
        travel_qs = TravelRow.objects.filter(
            organisation=org,
        )
        scope3_approved = travel_qs.filter(status='APPROVED')
        scope3_total_kg = scope3_approved.aggregate(t=Sum('co2e_kg'))['t'] or 0

        scope3_by_cat = {
            'business_travel_air':    0.0,
            'business_travel_hotel':  0.0,
            'business_travel_ground': 0.0,
        }
        for row in scope3_approved.values('ghg_category').annotate(total=Sum('co2e_kg')):
            cat   = (row['ghg_category'] or '').lower()
            val_t = round(float(row['total'] or 0) / 1000, 4)
            if 'air' in cat:
                scope3_by_cat['business_travel_air'] += val_t
            elif 'hotel' in cat:
                scope3_by_cat['business_travel_hotel'] += val_t
            else:
                scope3_by_cat['business_travel_ground'] += val_t

        # ── Data quality metrics ──────────────────────────────────────────────
        total_rows    = (sap_qs.count() + util_qs.count() + travel_qs.count()) or 1
        approved_rows = (
            scope1_approved.count() +
            scope2_approved.count() +
            scope3_approved.count()
        )
        completeness = round(approved_rows / total_rows * 100, 1)

        major_variance = util_qs.filter(
            co2_comparison_status='MAJOR_VARIANCE'
        ).count() + sap_qs.filter(
            co2_comparison_status='MAJOR_VARIANCE'
        ).count()

        pending_rows = (
            sap_qs.filter(status='PENDING').count() +
            util_qs.filter(status='PENDING').count() +
            travel_qs.filter(status='PENDING').count()
        )

        from apps.ingestion.models import RowComment
        unresolved_findings = RowComment.objects.filter(
            organisation=org,
            is_finding=True,
            resolved=False,
        ).count()

        # ── Totals in tonnes ──────────────────────────────────────────────────
        s1_t = round(float(scope1_total_kg) / 1000, 4)
        s2_t = round(float(scope2_total_kg) / 1000, 4)
        s3_t = round(float(scope3_total_kg) / 1000, 4)

        return Response({
            'reporting_period': fy,
            'organisation':     org.name,
            'scope_1': {
                'total_co2e_tonnes':      s1_t,
                'by_fuel_type':           scope1_by_fuel,
                'emission_factor_source': scope1_ef['source_name'] if scope1_ef else 'IPCC_2006',
                'row_count':              sap_qs.count(),
                'approved_row_count':     scope1_approved.count(),
            },
            'scope_2': {
                'total_co2e_tonnes':      s2_t,
                'total_kwh_consumed':     round(float(scope2_kwh), 2),
                'emission_factor_used':   cea_factor.factor_value if cea_factor else None,
                'emission_factor_source': 'CEA_V20',
                'method':                 'location_based',
                'fy_factor_used':         cea_factor.valid_from_fy if cea_factor else None,
                'row_count':              util_qs.count(),
                'approved_row_count':     scope2_approved.count(),
            },
            'scope_3': {
                'total_co2e_tonnes': s3_t,
                'by_category':       scope3_by_cat,
                'row_count':         travel_qs.count(),
                'approved_row_count': scope3_approved.count(),
            },
            'total_co2e_tonnes': round(s1_t + s2_t + s3_t, 4),
            'data_quality': {
                'rows_with_major_co2_variance':   major_variance,
                'rows_pending_approval':          pending_rows,
                'rows_with_unresolved_findings':  unresolved_findings,
                'completeness_pct':               completeness,
            },
            'generated_at':  date.today().isoformat(),
            'generated_by':  request.user.email or request.user.username,
        })
