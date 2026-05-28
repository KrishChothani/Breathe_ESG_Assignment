from django.urls import path
from .views import BRSRSummaryView
from .forecast_views import EmissionsForecastView

urlpatterns = [
    path('brsr-summary/',      BRSRSummaryView.as_view(),       name='brsr-summary'),
    path('emissions-forecast/', EmissionsForecastView.as_view(), name='emissions-forecast'),
]
