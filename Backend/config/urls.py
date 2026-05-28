"""
Root URL Configuration
======================
All app routers are versioned under /api/v1/.
Auth endpoints live under /api/v1/auth/ (JWT login + refresh + me).
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/',            include('apps.users.urls')),
    path('api/v1/organisations/',   include('apps.organisations.urls')),
    path('api/v1/ingestion/',       include('apps.ingestion.urls')),
    path('api/v1/emissions/',       include('apps.emissions.urls')),
    path('api/v1/review/',          include('apps.review.urls')),
    path('api/v1/reports/',         include('apps.reports.urls')),
]

# Serve uploaded files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
