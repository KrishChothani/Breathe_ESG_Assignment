from django.urls import path
from .views import (
    OrganisationMeView,
    MemberListView,
    InviteMemberView,
    MemberDetailView,
    SwitchOrganisationView,
)

urlpatterns = [
    path('me/',                    OrganisationMeView.as_view(),    name='org-me'),
    path('members/',               MemberListView.as_view(),         name='org-members'),
    path('members/invite/',        InviteMemberView.as_view(),       name='org-invite'),
    path('members/<uuid:pk>/',     MemberDetailView.as_view(),       name='org-member-detail'),
    path('switch/',                SwitchOrganisationView.as_view(), name='org-switch'),
]
