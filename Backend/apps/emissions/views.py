"""
apps/emissions/views.py — Multi-tenant edition (fixed)
=======================================================
Every view resolves org via core.tenant.get_active_organisation(request)
which decodes the JWT directly — reliable regardless of DRF auth order.
"""

import csv
import io
from datetime import date

from django.db.models import Count, Min, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from core.mixins import TenantQuerysetMixin, TenantCreateMixin
from core.permissions import IsTenantAnalyst, IsTenantAdmin, SameOrganisationOnly
from core.tenant import get_active_organisation, get_active_role
from core.pagination import StandardResultsPagination
from .models import SAPRow, UtilityRow, TravelRow, PlantLookup
from .serializers import (
    SAPRowSerializer, UtilityRowSerializer, TravelRowSerializer,
    PlantLookupSerializer, PlantLookupCreateSerializer,
    PlantLookupBulkCSVSerializer,
)


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardView(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class   = StandardResultsPagination

    def get_serializer_class(self):
        row_type = self.request.query_params.get('type', 'SAP').upper()
        if row_type == 'UTILITY':
            return UtilityRowSerializer
        elif row_type == 'TRAVEL':
            return TravelRowSerializer
        return SAPRowSerializer

    def get_queryset(self):
        row_type      = self.request.query_params.get('type', 'SAP').upper()
        status_filter = self.request.query_params.get('status')
        org           = get_active_organisation(self.request)

        if org is None:
            return SAPRow.objects.none()

        if row_type == 'UTILITY':
            qs = UtilityRow.objects.filter(organisation=org)
        elif row_type == 'TRAVEL':
            qs = TravelRow.objects.filter(organisation=org)
        else:
            qs = SAPRow.objects.filter(organisation=org)

        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        return qs.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        row_type = request.query_params.get('type', 'SAP').upper()
        if row_type == 'FAILED':
            org = get_active_organisation(request)
            if not org:
                return Response({'count': 0, 'results': []})
            
            results = []
            
            for row in SAPRow.objects.select_related('raw_upload').filter(organisation=org, status='PARSE_FAILED'):
                results.append({
                    'id': str(row.id),
                    'source_type': 'SAP',
                    'filename': row.raw_upload.original_filename if row.raw_upload else '',
                    'failed_at': row.updated_at.isoformat(),
                    'parse_error': getattr(row, 'parse_error', ''),
                })
            for row in UtilityRow.objects.select_related('raw_upload').filter(organisation=org, status='PARSE_FAILED'):
                results.append({
                    'id': str(row.id),
                    'source_type': 'UTILITY',
                    'filename': row.raw_upload.original_filename if row.raw_upload else '',
                    'failed_at': row.updated_at.isoformat(),
                    'parse_error': getattr(row, 'parse_error', ''),
                })
            for row in TravelRow.objects.select_related('raw_upload').filter(organisation=org, status='PARSE_FAILED'):
                results.append({
                    'id': str(row.id),
                    'source_type': 'TRAVEL',
                    'filename': row.raw_upload.original_filename if row.raw_upload else '',
                    'failed_at': row.updated_at.isoformat(),
                    'parse_error': getattr(row, 'parse_error', ''),
                })
                
            results.sort(key=lambda x: x['failed_at'], reverse=True)
            # Standard pagination wrapper for frontend compat
            page = int(request.query_params.get('page', 1))
            page_size = 50
            start = (page - 1) * page_size
            end = start + page_size
            
            return Response({
                'count': len(results),
                'next': None,
                'previous': None,
                'results': results[start:end]
            })
            
        return super().get(request, *args, **kwargs)


class DashboardStatsView(APIView):
    """GET /api/v1/emissions/dashboard/stats/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db.models import Sum
        org = get_active_organisation(request)
        if org is None:
            return Response({
                "total_rows": 0, "total_co2e": 0,
                "pending_review": 0, "sources": []
            })

        stats         = []
        total_co2e    = 0
        total_rows    = 0
        total_pending = 0

        for source_name, model in [('SAP', SAPRow), ('UTILITY', UtilityRow), ('TRAVEL', TravelRow)]:
            aggs = model.objects.filter(organisation=org).aggregate(
                total   = Count('id'),
                parsed  = Count('id', filter=Q(status__in=['PENDING', 'APPROVED', 'LOCKED'])),
                failed  = Count('id', filter=Q(status='PARSE_FAILED')),
                flagged = Count('id', filter=Q(status='FLAGGED')),
                pending = Count('id', filter=Q(status='PENDING')),
                co2e_sum= Sum('co2e_kg'),
            )
            total = aggs['total'] or 0
            stats.append({
                'source':  source_name,
                'label':   f"{source_name.capitalize()} Data",
                'total':   total,
                'parsed':  aggs['parsed'] or 0,
                'failed':  aggs['failed'] or 0,
                'flagged': aggs['flagged'] or 0,
            })
            total_rows    += total
            total_pending += (aggs['pending'] or 0)
            if aggs['co2e_sum']:
                total_co2e += float(aggs['co2e_sum'])

        return Response({
            'total_rows':     total_rows,
            'total_co2e':     total_co2e,
            'pending_review': total_pending,
            'sources':        stats,
        })


# ── PlantLookup ───────────────────────────────────────────────────────────────

class PlantLookupListCreateView(generics.ListCreateAPIView):
    queryset           = PlantLookup.objects.select_related('added_by', 'grid_emission_factor')
    permission_classes = [IsAuthenticated]
    pagination_class   = StandardResultsPagination

    def get_serializer_class(self):
        return PlantLookupCreateSerializer if self.request.method == 'POST' else PlantLookupSerializer

    def get_queryset(self):
        org = get_active_organisation(self.request)
        if org is None:
            return PlantLookup.objects.none()
        qs = PlantLookup.objects.filter(organisation=org).select_related('added_by', 'grid_emission_factor')

        country   = self.request.query_params.get('country')
        region    = self.request.query_params.get('region')
        is_active = self.request.query_params.get('is_active')
        search    = self.request.query_params.get('search')

        if country:
            qs = qs.filter(country__iexact=country)
        if region:
            qs = qs.filter(region=region.upper())
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() in ('true', '1', 'yes')))
        if search:
            qs = qs.filter(
                Q(werks_code__icontains=search) |
                Q(plant_name__icontains=search) |
                Q(city__icontains=search) |
                Q(country__icontains=search)
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(
            organisation=get_active_organisation(self.request),
            added_by=self.request.user,
        )


class PlantLookupDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return PlantLookupCreateSerializer if self.request.method in ('PATCH', 'PUT') else PlantLookupSerializer

    def get_queryset(self):
        org = get_active_organisation(self.request)
        if org is None:
            return PlantLookup.objects.none()
        return PlantLookup.objects.filter(organisation=org)

    def destroy(self, request, *args, **kwargs):
        if get_active_role(request) != 'ADMIN':
            return Response(
                {'error': 'Only Org Admins can delete plant codes.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class PlantLookupDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        org   = get_active_organisation(request)
        plant = get_object_or_404(PlantLookup, pk=pk, organisation=org)
        plant.is_active = False
        note  = f"\n[Deactivated by {request.user.username} on {date.today()}]"
        plant.notes = (plant.notes or '') + note
        plant.save()
        return Response({
            'message':    f"Plant {plant.werks_code} deactivated.",
            'werks_code': plant.werks_code,
            'is_active':  False,
        })


class PlantLookupBulkCSVImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser]
    REQUIRED_COLUMNS   = {'werks_code', 'plant_name', 'city', 'country', 'region'}

    def post(self, request):
        serializer = PlantLookupBulkCSVSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        csv_file  = request.FILES['file']
        overwrite = str(request.data.get('overwrite_existing', 'false')).lower() in ('true', '1', 'yes')
        org       = get_active_organisation(request)

        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be a .csv'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader  = csv.DictReader(io.StringIO(decoded))
        except Exception as exc:
            return Response({'error': f"Could not read CSV: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        headers_lower = {h.strip().lower() for h in (reader.fieldnames or [])}
        missing = self.REQUIRED_COLUMNS - headers_lower
        if missing:
            return Response({'error': f"CSV missing required columns: {missing}"}, status=status.HTTP_400_BAD_REQUEST)

        created = updated = skipped = 0
        errors  = []

        for row_num, row in enumerate(reader, start=2):
            row        = {k.strip().lower(): v.strip() for k, v in row.items()}
            werks_code = row.get('werks_code', '').upper().strip()
            if not werks_code:
                errors.append({'row': row_num, 'error': 'werks_code is empty'}); skipped += 1; continue

            country = row.get('country', '').upper().strip()
            if len(country) != 2:
                errors.append({'row': row_num, 'werks_code': werks_code, 'error': f"Invalid country '{country}'"}); skipped += 1; continue

            defaults = {
                'plant_name': row.get('plant_name', ''), 'city': row.get('city', ''),
                'state': row.get('state', ''), 'country': country,
                'postal_code': row.get('postal_code', ''),
                'region': row.get('region', 'ASIA_PACIFIC').upper(),
                'plant_type': row.get('plant_type', 'MANUFACTURING').upper(),
                'default_scope': row.get('default_scope', 'SCOPE_1').upper(),
                'address_line': row.get('address_line', ''),
                'notes': row.get('notes', ''), 'added_by': request.user,
            }

            existing = PlantLookup.objects.filter(organisation=org, werks_code=werks_code).first()
            if existing:
                if overwrite:
                    for field, value in defaults.items():
                        if field != 'added_by':
                            setattr(existing, field, value)
                    existing.save(); updated += 1
                else:
                    errors.append({'row': row_num, 'werks_code': werks_code,
                                   'error': 'Already exists (set overwrite_existing=true to update)'}); skipped += 1
            else:
                PlantLookup.objects.create(organisation=org, werks_code=werks_code, **defaults); created += 1

        return Response(
            {'message': 'Bulk import complete', 'created': created, 'updated': updated, 'skipped': skipped, 'errors': errors},
            status=status.HTTP_207_MULTI_STATUS,
        )


class UnresolvedWERKSView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_active_organisation(request)
        if org is None:
            return Response({'total_unresolved_codes': 0, 'unresolved': []})
        known_codes = PlantLookup.objects.filter(organisation=org).values_list('werks_code', flat=True)
        unresolved  = (
            SAPRow.objects
            .filter(organisation=org)
            .exclude(plant_code__in=known_codes)
            .values('plant_code')
            .annotate(
                row_count       = Count('id'),
                first_seen      = Min('document_date'),
                sample_material = Min('material_description'),
            )
            .order_by('-row_count')
        )
        return Response({
            'total_unresolved_codes': unresolved.count(),
            'unresolved': list(unresolved),
        })


class PlantLookupExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org    = get_active_organisation(request)
        if org is None:
            return Response({'error': 'No active organisation'}, status=403)
        plants = PlantLookup.objects.filter(organisation=org).order_by('country', 'werks_code')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="plant_lookup_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['werks_code', 'plant_name', 'city', 'state', 'country',
                         'postal_code', 'region', 'plant_type', 'default_scope',
                         'address_line', 'is_active', 'notes'])
        for p in plants:
            writer.writerow([p.werks_code, p.plant_name, p.city, p.state, p.country,
                             p.postal_code, p.region, p.plant_type, p.default_scope,
                             p.address_line, p.is_active, p.notes])
        return response
