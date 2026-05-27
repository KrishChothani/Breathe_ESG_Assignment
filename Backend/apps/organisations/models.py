"""
apps/organisations — BreatheESG multi-tenant Organisation app.

Models:
  Organisation         — one row per company/client
  OrganisationMembership — links Users to Organisations with a per-org role
"""

import uuid
from django.db import models
from django.utils.text import slugify


class Organisation(models.Model):
    """
    One Organisation = one tenant.
    Every piece of data in the system is scoped to exactly one Organisation.
    """

    class SubscriptionPlan(models.TextChoices):
        FREE       = 'FREE',       'Free'
        STARTER    = 'STARTER',    'Starter'
        PRO        = 'PRO',        'Pro'
        ENTERPRISE = 'ENTERPRISE', 'Enterprise'

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, help_text="Used in URLs — auto-generated from name")

    industry  = models.CharField(max_length=100, blank=True, help_text="e.g. Manufacturing, Logistics, Technology")
    country   = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 e.g. IN, DE, GB")

    subscription_plan = models.CharField(
        max_length=20,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
    )

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['name']
        verbose_name = 'Organisation'
        verbose_name_plural = 'Organisations'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Organisation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.slug})"


class OrganisationMembership(models.Model):
    """
    Links a User to an Organisation with a specific role.
    Role here overrides the legacy User.role field for all permission checks.
    A user can belong to multiple organisations (e.g. a consultant), but
    only operates in one at a time (enforced via JWT claim).
    """

    class Role(models.TextChoices):
        ADMIN    = 'ADMIN',    'Admin — full access including user management'
        ANALYST  = 'ANALYST',  'Analyst — can view, upload, approve, reject rows'
        AUDITOR  = 'AUDITOR',  'Auditor — read-only, LOCKED rows only'
        VIEWER   = 'VIEWER',   'Viewer — read-only, approved and locked rows'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role      = models.CharField(max_length=20, choices=Role.choices, default=Role.ANALYST)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('organisation', 'user')]
        verbose_name = 'Organisation Membership'
        verbose_name_plural = 'Organisation Memberships'
        ordering = ['organisation__name', 'role']

    def __str__(self):
        return f"{self.user.email} → {self.organisation.name} [{self.role}]"
