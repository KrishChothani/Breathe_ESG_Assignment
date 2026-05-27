from django.urls import path
from .views import (
    DashboardView, DashboardStatsView,
    PlantLookupListCreateView, PlantLookupDetailView,
    PlantLookupDeactivateView, PlantLookupBulkCSVImportView,
    UnresolvedWERKSView, PlantLookupExportCSVView,
)
from .chart_views import (
    ChartTrendView,
    ChartScopeBreakdownView,
    ChartBySourceView,
    ChartByPlantView,
    ChartIngestionActivityView,
    ChartReviewPipelineView,
)

urlpatterns = [
    # ── Dashboard / row listing ───────────────────────────────────────────────
    path('dashboard/',        DashboardView.as_view(),      name='dashboard'),
    path('dashboard/stats/',  DashboardStatsView.as_view(), name='dashboard-stats'),

    # ── Chart endpoints ───────────────────────────────────────────────────────
    path('charts/trend/',              ChartTrendView.as_view(),             name='chart-trend'),
    path('charts/scope-breakdown/',    ChartScopeBreakdownView.as_view(),    name='chart-scope'),
    path('charts/by-source/',          ChartBySourceView.as_view(),          name='chart-by-source'),
    path('charts/by-plant/',           ChartByPlantView.as_view(),           name='chart-by-plant'),
    path('charts/ingestion-activity/', ChartIngestionActivityView.as_view(), name='chart-ingestion'),
    path('charts/review-pipeline/',    ChartReviewPipelineView.as_view(),    name='chart-review'),

    # ── Plant Lookup — order matters: specifics before <uuid:pk> ─────────────
    path('plant-lookup/',
         PlantLookupListCreateView.as_view(),
         name='plant-lookup-list-create'),

    path('plant-lookup/bulk-import/',
         PlantLookupBulkCSVImportView.as_view(),
         name='plant-lookup-bulk-import'),

    path('plant-lookup/unresolved/',
         UnresolvedWERKSView.as_view(),
         name='plant-lookup-unresolved'),

    path('plant-lookup/export/',
         PlantLookupExportCSVView.as_view(),
         name='plant-lookup-export'),

    path('plant-lookup/<uuid:pk>/',
         PlantLookupDetailView.as_view(),
         name='plant-lookup-detail'),

    path('plant-lookup/<uuid:pk>/deactivate/',
         PlantLookupDeactivateView.as_view(),
         name='plant-lookup-deactivate'),
]
