from django.urls import path
from .views import BRSRSummaryView

urlpatterns = [
    path('brsr-summary/', BRSRSummaryView.as_view(), name='brsr-summary'),
]
