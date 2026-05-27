from django.urls import path
from .views import ApproveView, RejectView, LockView

urlpatterns = [
    path('approve/', ApproveView.as_view(), name='approve'),
    path('reject/', RejectView.as_view(), name='reject'),
    path('lock/', LockView.as_view(), name='lock'),
]
