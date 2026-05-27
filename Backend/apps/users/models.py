"""
apps/users/models.py
====================
Extended User model for BreatheESG multi-tenant SaaS.

Role is now primarily stored on OrganisationMembership, not on User directly.
The User.role field is kept as a fallback / superuser override.

active_organisation and active_role are derived from the JWT claims that are
attached to request.user by TenantMiddleware (core/middleware.py).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended user model. Role is now per-organisation (on OrganisationMembership).
    User.role is kept for Django admin / superuser use only.
    """

    class Role(models.TextChoices):
        ANALYST = 'ANALYST', 'Analyst'
        ADMIN   = 'ADMIN',   'Admin'
        AUDITOR = 'AUDITOR', 'Auditor'
        VIEWER  = 'VIEWER',  'Viewer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ANALYST,
        db_index=True,
        help_text="Fallback role for Django admin. In API context, role comes from OrganisationMembership.",
    )

    class Meta(AbstractUser.Meta):
        verbose_name        = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    # ── Active-organisation helpers (set by TenantMiddleware from JWT) ────────

    @property
    def active_organisation(self):
        """
        Returns the Organisation the user is currently operating in.
        The value is injected by TenantMiddleware from the JWT claim
        `organisation_id` and cached on the request user as `_active_org`.
        """
        return getattr(self, '_active_org', None)

    @active_organisation.setter
    def active_organisation(self, org):
        self._active_org = org

    @property
    def active_role(self):
        """
        Returns role string from the JWT claim `role` (set at login to the
        membership role). Falls back to User.role for superusers / admin use.
        """
        jwt_role = getattr(self, '_active_role', None)
        if jwt_role:
            return jwt_role
        # Fallback: look up from membership
        org = self.active_organisation
        if org:
            from apps.organisations.models import OrganisationMembership
            try:
                m = OrganisationMembership.objects.get(
                    user=self, organisation=org, is_active=True
                )
                return m.role
            except OrganisationMembership.DoesNotExist:
                pass
        return self.role  # last-resort fallback

    @active_role.setter
    def active_role(self, role):
        self._active_role = role

    # ── Legacy helpers (kept for backwards compat) ────────────────────────────

    @property
    def is_analyst(self):
        return self.active_role in ('ANALYST', 'ADMIN')

    @property
    def is_admin_user(self):
        return self.active_role == 'ADMIN'

    @property
    def is_auditor(self):
        return self.active_role in ('AUDITOR', 'ADMIN')
