"""
core/permissions.py
===================
Permission classes for BreatheESG multi-tenant API.
All role checks read from the JWT via core.tenant.get_active_role().
"""

from rest_framework import permissions
from core.tenant import get_active_role, get_active_organisation


# ── Legacy (kept for backwards compat) ────────────────────────────────────────

class IsAnalyst(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_active_role(request)
        is_auth = bool(request.user and request.user.is_authenticated)
        print(f"[DEBUG] IsAnalyst check -> User: {request.user}, Is_auth: {is_auth}, Role: {role}")
        return is_auth and role in ('ANALYST', 'ADMIN')


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_active_role(request)
        return bool(request.user and request.user.is_authenticated and role == 'ADMIN')


class IsAuditor(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_active_role(request)
        return bool(request.user and request.user.is_authenticated and role in ('AUDITOR', 'ADMIN'))


# ── Tenant-aware permissions ───────────────────────────────────────────────────

class IsTenantAdmin(permissions.BasePermission):
    message = "You must be an Organisation Admin to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_active_role(request) == 'ADMIN'


class IsTenantAnalyst(permissions.BasePermission):
    message = "You must be an Analyst or Admin to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_active_role(request) in ('ADMIN', 'ANALYST')


class IsTenantAuditor(permissions.BasePermission):
    message = "You must be an Auditor, Analyst, or Admin to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_active_role(request) in ('ADMIN', 'ANALYST', 'AUDITOR')


class SameOrganisationOnly(permissions.BasePermission):
    message = "You do not have permission to access data from another organisation."

    def has_object_permission(self, request, view, obj):
        org = get_active_organisation(request)
        if org is None:
            return False
        obj_org = getattr(obj, 'organisation', None)
        if obj_org is None:
            return True
        return obj_org == org
