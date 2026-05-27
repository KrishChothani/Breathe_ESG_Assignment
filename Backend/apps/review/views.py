"""
apps/review/views.py — Multi-tenant edition (fixed)
Row lookups are scoped to the active organisation via core.tenant.
"""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsTenantAnalyst
from core.tenant import get_active_organisation
from apps.emissions.models import SAPRow, UtilityRow, TravelRow


def _get_row(row_id, org):
    """Find a row by UUID, scoped to active organisation."""
    for Model in (SAPRow, UtilityRow, TravelRow):
        try:
            return Model.objects.get(id=row_id, organisation=org)
        except ObjectDoesNotExist:
            continue
    return None


class ApproveView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAnalyst]

    def post(self, request, *args, **kwargs):
        row_id = request.data.get('row_id')
        if not row_id:
            return Response({"error": "row_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        org = get_active_organisation(request)
        row = _get_row(row_id, org)
        if not row:
            return Response({"error": "Row not found"}, status=status.HTTP_404_NOT_FOUND)
        from apps.ingestion.models import RowComment
        if RowComment.objects.filter(row_id=row_id, is_finding=True, resolved=False).exists():
            return Response({"error": "Cannot approve row with unresolved findings."}, status=status.HTTP_400_BAD_REQUEST)

        row._performed_by = request.user
        row.status = 'APPROVED'
        row.save(update_fields=['status', 'updated_at'])
        return Response({"status": "approved", "id": row.id})


class RejectView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAnalyst]

    def post(self, request, *args, **kwargs):
        row_id = request.data.get('row_id')
        if not row_id:
            return Response({"error": "row_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        org = get_active_organisation(request)
        row = _get_row(row_id, org)
        if not row:
            return Response({"error": "Row not found"}, status=status.HTTP_404_NOT_FOUND)
        row._performed_by = request.user
        row.status = 'REJECTED'
        row.save(update_fields=['status', 'updated_at'])
        return Response({"status": "rejected", "id": row.id})


class LockView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAnalyst]

    def post(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response({"error": "ids list is required"}, status=status.HTTP_400_BAD_REQUEST)

        org           = get_active_organisation(request)
        updated_count = 0
        for Model in (SAPRow, UtilityRow, TravelRow):
            rows = Model.objects.filter(id__in=ids, organisation=org)
            for row in rows:
                row._performed_by = request.user
                row.status = 'LOCKED'
                row.save(update_fields=['status', 'updated_at'])
                updated_count += 1

        return Response({"status": "locked", "count": updated_count})
