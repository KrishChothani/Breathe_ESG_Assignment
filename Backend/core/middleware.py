"""
core/middleware.py
==================
TenantMiddleware — reads JWT claims (organisation_id, role) from the
Authorization header and sets them on request.user so that:

  request.user.active_organisation  →  Organisation instance
  request.user.active_role          →  "ADMIN" | "ANALYST" | "AUDITOR" | "VIEWER"

This runs AFTER DRF's JWT authentication, so request.user is already
the authenticated User object.
"""

import logging
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger(__name__)


def _extract_jwt_claims(request):
    """Return the decoded JWT payload dict if present, else {}."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {}
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(auth_header.split(" ", 1)[1])
        return dict(token.payload)
    except Exception:
        return {}


class TenantMiddleware:
    """
    Sets active_organisation and active_role on request.user from JWT claims.

    Must be placed AFTER django.contrib.auth.middleware.AuthenticationMiddleware
    in MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only process JWT-bearing requests
        if request.headers.get("Authorization", "").startswith("Bearer "):
            self._attach_tenant(request)
        response = self.get_response(request)
        return response

    def _attach_tenant(self, request):
        claims = _extract_jwt_claims(request)
        org_id = claims.get("organisation_id")
        role   = claims.get("role")

        if not org_id:
            return

        # Lazily resolve the Organisation to avoid a DB hit on every static asset
        def _get_org():
            from apps.organisations.models import Organisation
            try:
                return Organisation.objects.get(id=org_id, is_active=True)
            except Organisation.DoesNotExist:
                logger.warning("TenantMiddleware: organisation_id=%s not found in JWT", org_id)
                return None

        # We need request.user to be resolved — DRF sets it lazily too
        # Defer until after DRF auth by wrapping in a callable
        original_user = request.user

        class TenantUser(SimpleLazyObject):
            pass

        if hasattr(original_user, 'is_authenticated') and original_user.is_authenticated:
            original_user._active_org  = SimpleLazyObject(_get_org)
            original_user._active_role = role
