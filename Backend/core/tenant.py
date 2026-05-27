"""
core/tenant.py
==============
Single source of truth for resolving the active Organisation and Role
from the JWT on every DRF request.

DRF authenticates the user lazily during view dispatch — AFTER Django
middleware has already run. So middleware cannot set org context on
request.user reliably.

These functions decode the JWT directly from the Authorization header.
Results are cached on request.user to avoid repeated DB hits per request.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


def _decode_jwt_payload(request):
    """Return the decoded JWT payload dict, or {} on failure."""
    # If DRF JWTAuthentication already ran, the token is in request.auth
    auth_obj = getattr(request, 'auth', None)
    if auth_obj and hasattr(auth_obj, 'payload'):
        return auth_obj.payload

    # Fallback if accessed outside DRF views
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.lower().startswith('bearer '):
        return {}
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(auth.split(' ', 1)[1])
        return dict(token.payload)
    except Exception:
        return {}


def get_active_organisation(request):
    """
    Returns the Organisation the authenticated user is currently operating in.
    Decodes organisation_id from the JWT and queries the DB once per request
    (cached on request.user._active_org).

    Returns None if:
      - No JWT present
      - JWT has no organisation_id claim
      - Organisation not found / inactive
    """
    user = getattr(request, 'user', None)
    if user is None:
        return None

    # Already cached this request
    cached = getattr(user, '_active_org', None)
    if cached is not None:
        return cached

    payload = _decode_jwt_payload(request)
    org_id  = payload.get('organisation_id')
    role    = payload.get('role')

    if not org_id:
        logger.warning("get_active_organisation: org_id missing in payload. Payload: %s", payload)
        return None

    try:
        from apps.organisations.models import Organisation
        org = Organisation.objects.get(id=org_id, is_active=True)
        # Cache on user object for this request
        user._active_org  = org
        user._active_role = role
        return org
    except Exception as exc:
        logger.warning("get_active_organisation: could not resolve org_id=%s — %s", org_id, exc)
        return None


def get_active_role(request):
    """
    Returns the role string ('ADMIN','ANALYST','AUDITOR','VIEWER') for the
    current user in their active organisation.

    Calling get_active_organisation() first caches both org and role together.
    """
    user = getattr(request, 'user', None)
    if user is None:
        return None

    # Try cached first
    role = getattr(user, '_active_role', None)
    if role:
        return role

    # Decode JWT (also caches _active_org/_active_role as side effect)
    get_active_organisation(request)
    return getattr(user, '_active_role', None) or getattr(user, 'role', None)
