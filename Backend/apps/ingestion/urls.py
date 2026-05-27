from django.urls import path
from .views import (
    UploadView,
    NavanTripImportView,
    NavanBatchSyncView,
    BillOCRExtractView,
    BillOCRConfirmView,
    AuditLogListView,
    RowCommentListCreateView,
    RowCommentResolveView,
    ProvenanceExportView,
)

urlpatterns = [
    # Generic upload (SAP / Utility file uploads)
    path('upload/', UploadView.as_view(), name='upload'),

    # Navan Trips API integration
    path('travel/navan/import/', NavanTripImportView.as_view(), name='navan-trip-import'),
    path('travel/navan/sync/',   NavanBatchSyncView.as_view(),  name='navan-batch-sync'),

    # AI Bill OCR — Gemini Vision
    path('utility/ocr-extract/', BillOCRExtractView.as_view(), name='bill-ocr-extract'),
    path('utility/ocr-confirm/', BillOCRConfirmView.as_view(), name='bill-ocr-confirm'),

    # Audit & Comments
    path('audit-logs/', AuditLogListView.as_view(), name='audit-logs'),
    path('rows/<str:source>/<str:row_id>/comments/', RowCommentListCreateView.as_view(), name='row-comments'),
    path('rows/comments/<uuid:pk>/resolve/', RowCommentResolveView.as_view(), name='resolve-comment'),
    
    # Export
    path('export/provenance/', ProvenanceExportView.as_view(), name='export-provenance'),
]
