"""
apps/emissions/chart_views.py
==============================
Six dedicated chart API endpoints for the BreatheESG Analytics Dashboard.
All views decode org from JWT directly via core.tenant.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth, TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.tenant import get_active_organisation
from .models import SAPRow, UtilityRow, TravelRow, PlantLookup
from apps.ingestion.models import RawUpload


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_floor(range_param):
    """Return the start date for the given range string, or None for 'all'."""
    today = date.today()
    mapping = {
        '7d':  today - timedelta(days=7),
        '30d': today - timedelta(days=30),
        '90d': today - timedelta(days=90),
        '6m':  today - relativedelta(months=6),
        '1y':  today - relativedelta(years=1),
        'all': None,
    }
    return mapping.get(range_param, today - timedelta(days=30))


def _month_label(dt):
    """'2024-01-01' or date object → '2024-01'."""
    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m')
    return str(dt)[:7]


# ── 1. Trend: monthly emissions by source ─────────────────────────────────────

class ChartTrendView(APIView):
    """GET /api/v1/emissions/charts/trend/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org        = get_active_organisation(request)
        range_p    = request.query_params.get('range', '6m')
        floor_date = _date_floor(range_p)

        if org is None:
            return Response([])

        def monthly_sum(Model, date_field):
            qs = Model.objects.filter(organisation=org, co2e_kg__isnull=False)
            if floor_date:
                qs = qs.filter(**{f'{date_field}__gte': floor_date})
            return (
                qs.annotate(month=TruncMonth(date_field))
                  .values('month')
                  .annotate(total=Sum('co2e_kg'))
                  .order_by('month')
            )

        sap_qs     = monthly_sum(SAPRow,     'document_date')
        utility_qs = monthly_sum(UtilityRow, 'billing_start')
        travel_qs  = monthly_sum(TravelRow,  'travel_date')

        # Merge into a dict keyed by month
        months = {}
        for row in sap_qs:
            key = _month_label(row['month'])
            months.setdefault(key, {'month': key, 'SAP': 0, 'UTILITY': 0, 'TRAVEL': 0})
            months[key]['SAP'] = float(row['total'] or 0)

        for row in utility_qs:
            key = _month_label(row['month'])
            months.setdefault(key, {'month': key, 'SAP': 0, 'UTILITY': 0, 'TRAVEL': 0})
            months[key]['UTILITY'] = float(row['total'] or 0)

        for row in travel_qs:
            key = _month_label(row['month'])
            months.setdefault(key, {'month': key, 'SAP': 0, 'UTILITY': 0, 'TRAVEL': 0})
            months[key]['TRAVEL'] = float(row['total'] or 0)

        result = []
        for key in sorted(months.keys()):
            m = months[key]
            m['total'] = round(m['SAP'] + m['UTILITY'] + m['TRAVEL'], 2)
            result.append(m)

        return Response(result)


# ── 2. Scope breakdown (donut) ────────────────────────────────────────────────

class ChartScopeBreakdownView(APIView):
    """GET /api/v1/emissions/charts/scope-breakdown/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org        = get_active_organisation(request)
        range_p    = request.query_params.get('range', '1y')
        floor_date = _date_floor(range_p)

        if org is None:
            return Response({'scope_1': 0, 'scope_2': 0, 'scope_3': 0, 'total': 0, 'unit': 'kgCO2e'})

        def _sum(Model, date_field):
            qs = Model.objects.filter(organisation=org, co2e_kg__isnull=False)
            if floor_date:
                qs = qs.filter(**{f'{date_field}__gte': floor_date})
            val = qs.aggregate(s=Sum('co2e_kg'))['s']
            return float(val or 0)

        scope_1 = _sum(SAPRow,     'document_date')  # direct combustion
        scope_2 = _sum(UtilityRow, 'billing_start')  # purchased electricity
        scope_3 = _sum(TravelRow,  'travel_date')    # business travel

        total = scope_1 + scope_2 + scope_3
        return Response({
            'scope_1': round(scope_1, 2),
            'scope_2': round(scope_2, 2),
            'scope_3': round(scope_3, 2),
            'total':   round(total, 2),
            'unit':    'kgCO2e',
        })


# ── 3. Emissions by activity/source (stacked bar) ────────────────────────────

class ChartBySourceView(APIView):
    """GET /api/v1/emissions/charts/by-source/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org        = get_active_organisation(request)
        range_p    = request.query_params.get('range', '6m')
        floor_date = _date_floor(range_p)

        if org is None:
            return Response([])

        # SAP rows → "fuel"
        sap_qs = SAPRow.objects.filter(organisation=org, co2e_kg__isnull=False)
        if floor_date:
            sap_qs = sap_qs.filter(document_date__gte=floor_date)
        sap_monthly = (
            sap_qs.annotate(month=TruncMonth('document_date'))
                  .values('month')
                  .annotate(fuel=Sum('co2e_kg'))
                  .order_by('month')
        )

        # Utility → "electricity"
        util_qs = UtilityRow.objects.filter(organisation=org, co2e_kg__isnull=False)
        if floor_date:
            util_qs = util_qs.filter(billing_start__gte=floor_date)
        util_monthly = (
            util_qs.annotate(month=TruncMonth('billing_start'))
                   .values('month')
                   .annotate(electricity=Sum('co2e_kg'))
                   .order_by('month')
        )

        # Travel split by segment_type
        travel_qs = TravelRow.objects.filter(organisation=org, co2e_kg__isnull=False)
        if floor_date:
            travel_qs = travel_qs.filter(travel_date__gte=floor_date)
        travel_monthly = (
            travel_qs.annotate(month=TruncMonth('travel_date'))
                     .values('month', 'segment_type')
                     .annotate(total=Sum('co2e_kg'))
                     .order_by('month')
        )

        months = {}

        def ensure(key):
            months.setdefault(key, {
                'month': key, 'fuel': 0, 'electricity': 0,
                'flights': 0, 'hotels': 0, 'ground_transport': 0,
            })

        for row in sap_monthly:
            key = _month_label(row['month'])
            ensure(key)
            months[key]['fuel'] = float(row['fuel'] or 0)

        for row in util_monthly:
            key = _month_label(row['month'])
            ensure(key)
            months[key]['electricity'] = float(row['electricity'] or 0)

        SEG_MAP = {'AIR': 'flights', 'HOTEL': 'hotels',
                   'CAR': 'ground_transport', 'RAIL': 'ground_transport',
                   'GROUND_TRANSPORT': 'ground_transport'}
        for row in travel_monthly:
            key     = _month_label(row['month'])
            seg_key = SEG_MAP.get(row['segment_type'], 'flights')
            ensure(key)
            months[key][seg_key] = months[key].get(seg_key, 0) + float(row['total'] or 0)

        return Response([months[k] for k in sorted(months.keys())])


# ── 4. Top facilities / plants ────────────────────────────────────────────────

class ChartByPlantView(APIView):
    """GET /api/v1/emissions/charts/by-plant/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org        = get_active_organisation(request)
        range_p    = request.query_params.get('range', '1y')
        top_n      = int(request.query_params.get('top', 10))
        floor_date = _date_floor(range_p)

        if org is None:
            return Response([])

        qs = SAPRow.objects.filter(organisation=org, co2e_kg__isnull=False)
        if floor_date:
            qs = qs.filter(document_date__gte=floor_date)

        plant_aggs = (
            qs.values('plant_code')
              .annotate(co2e_kg=Sum('co2e_kg'), row_count=Count('id'))
              .order_by('-co2e_kg')[:top_n]
        )

        # Build a lookup: werks_code → PlantLookup
        codes    = [r['plant_code'] for r in plant_aggs]
        lookups  = {
            p.werks_code: p
            for p in PlantLookup.objects.filter(organisation=org, werks_code__in=codes)
        }

        total_co2e = sum(float(r['co2e_kg'] or 0) for r in plant_aggs)

        result = []
        for row in plant_aggs:
            code  = row['plant_code']
            plant = lookups.get(code)
            co2e  = float(row['co2e_kg'] or 0)
            pct   = round((co2e / total_co2e * 100), 1) if total_co2e > 0 else 0
            result.append({
                'plant_code': code,
                'plant_name': plant.plant_name if plant else None,
                'city':       plant.city       if plant else None,
                'country':    plant.country    if plant else None,
                'co2e_kg':    round(co2e, 2),
                'percentage': pct,
                'resolved':   plant is not None,
            })

        return Response(result)


# ── 5. Ingestion activity (area chart) ────────────────────────────────────────

class ChartIngestionActivityView(APIView):
    """GET /api/v1/emissions/charts/ingestion-activity/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org        = get_active_organisation(request)
        range_p    = request.query_params.get('range', '30d')
        floor_date = _date_floor(range_p)

        if org is None:
            return Response([])

        qs = RawUpload.objects.filter(organisation=org)
        if floor_date:
            qs = qs.filter(created_at__date__gte=floor_date)

        daily = (
            qs.annotate(day=TruncDate('created_at'))
              .values('day')
              .annotate(
                  uploads       = Count('id'),
                  rows_ingested = Sum('row_count'),
              )
              .order_by('day')
        )

        # For failed rows, pull from SAP+Utility+Travel PARSE_FAILED per day
        result = []
        for row in daily:
            day_str = row['day'].strftime('%Y-%m-%d') if row['day'] else ''
            result.append({
                'date':          day_str,
                'uploads':       row['uploads'],
                'rows_ingested': int(row['rows_ingested'] or 0),
                'rows_failed':   0,   # enriched below
            })

        # Count parse failures per upload date
        fail_map = {}
        for Model in (SAPRow, UtilityRow, TravelRow):
            fails = (
                Model.objects
                .filter(organisation=org, status='PARSE_FAILED',
                        raw_upload__created_at__date__gte=floor_date if floor_date else date(2000, 1, 1))
                .annotate(day=TruncDate('raw_upload__created_at'))
                .values('day')
                .annotate(cnt=Count('id'))
            )
            for f in fails:
                key = f['day'].strftime('%Y-%m-%d') if f['day'] else ''
                fail_map[key] = fail_map.get(key, 0) + f['cnt']

        for entry in result:
            entry['rows_failed'] = fail_map.get(entry['date'], 0)

        return Response(result)


# ── 6. Review pipeline ────────────────────────────────────────────────────────

class ChartReviewPipelineView(APIView):
    """GET /api/v1/emissions/charts/review-pipeline/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_active_organisation(request)
        if org is None:
            return Response({
                'pending': 0, 'flagged': 0, 'approved': 0,
                'rejected': 0, 'locked': 0, 'total': 0, 'approval_rate': 0,
            })

        counts = {'pending': 0, 'flagged': 0, 'approved': 0, 'rejected': 0, 'locked': 0}
        for Model in (SAPRow, UtilityRow, TravelRow):
            agg = Model.objects.filter(organisation=org).aggregate(
                pending  = Count('id', filter=Q(status='PENDING')),
                flagged  = Count('id', filter=Q(status='FLAGGED')),
                approved = Count('id', filter=Q(status='APPROVED')),
                rejected = Count('id', filter=Q(status='REJECTED')),
                locked   = Count('id', filter=Q(status='LOCKED')),
            )
            for k in counts:
                counts[k] += (agg[k] or 0)

        total    = sum(counts.values())
        approved = counts['approved'] + counts['locked']
        rate     = round((approved / total * 100), 1) if total > 0 else 0.0

        return Response({**counts, 'total': total, 'approval_rate': rate})
