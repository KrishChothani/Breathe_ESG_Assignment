"""
core/mixins.py
==============
Reusable DRF view mixins that enforce tenant isolation.
Uses core.tenant.get_active_organisation() to decode org from JWT directly —
this is reliable regardless of DRF's lazy authentication order.
"""

from core.tenant import get_active_organisation


class TenantQuerysetMixin:
    """
    Filters get_queryset() to the current user's active organisation.
    Reads org directly from the JWT (not from middleware-set user attributes).
    """

    def get_queryset(self):
        org = get_active_organisation(self.request)
        if org is None:
            return super().get_queryset().none()
        return super().get_queryset().filter(organisation=org)


class TenantCreateMixin:
    """
    Injects `organisation` into serializer.save() on create.
    """

    def perform_create(self, serializer):
        org = get_active_organisation(self.request)
        serializer.save(organisation=org)
