"""
apps/chatbot/urls.py
====================
URL configuration for the chatbot app.
Mounted at /api/v1/chatbot/ in config/urls.py.
"""

from django.urls import path
from .views import ChatQueryView

urlpatterns = [
    path('query/', ChatQueryView.as_view(), name='chatbot-query'),
]
