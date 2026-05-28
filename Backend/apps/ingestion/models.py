"""
apps/ingestion/models.py
========================
RawUpload now belongs to an Organisation (multi-tenant).
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import PermissionDenied


class RawUpload(models.Model):
    """
    Represents a single file or API pull ingest event.
    Acts as the root anchor for every NormalisedRow that derives from it.
    Scoped to an Organisation for full tenant isolation.
    """

    class SourceType(models.TextChoices):
        SAP     = 'SAP',     'SAP Flat File Export'
        UTILITY = 'UTILITY', 'Utility Portal CSV'
        TRAVEL  = 'TRAVEL',  'Concur / Navan Travel API'

    class Status(models.TextChoices):
        UPLOADED       = 'UPLOADED',       'Uploaded — awaiting processing'
        PROCESSING     = 'PROCESSING',     'Processing in progress'
        DONE           = 'DONE',           'Parsing complete'
        FAILED         = 'FAILED',         'Parsing failed'
        OCR_EXTRACTED  = 'OCR_EXTRACTED',  'AI OCR extracted — awaiting confirmation'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Tenant scope ──────────────────────────────────────────────────────────
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='raw_uploads',
        db_index=True,
    )

    source_type       = models.CharField(max_length=20, choices=SourceType.choices)
    file              = models.FileField(upload_to='raw_uploads/', null=True, blank=True)
    original_filename = models.CharField(max_length=512, blank=True)
    status            = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True
    )
    row_count  = models.IntegerField(null=True, blank=True)
    error_log  = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploads',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ['-created_at']
        verbose_name    = 'Raw Upload'
        verbose_name_plural = 'Raw Uploads'

    def __str__(self):
        return f"[{self.source_type}] {self.original_filename or self.id} — {self.status}"


class Airport(models.Model):
    """
    Lookup table for global airports, loaded from OurAirports CSV.
    Used for parsing travel data and calculating flight distances.
    """
    ident = models.CharField(max_length=10, unique=True)
    iata_code = models.CharField(max_length=4, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    airport_type = models.CharField(max_length=50)
    iso_country = models.CharField(max_length=2)
    iso_region = models.CharField(max_length=10)
    municipality = models.CharField(max_length=255, null=True, blank=True)
    continent = models.CharField(max_length=2, null=True, blank=True)

    class Meta:
        ordering = ['ident']
        verbose_name = 'Airport'
        verbose_name_plural = 'Airports'

    def __str__(self):
        return f"{self.ident} ({self.iata_code or 'No IATA'}) - {self.name}"

class AuditLog(models.Model):
    class Action(models.TextChoices):
        INGESTED = 'INGESTED', 'Ingested'
        FLAGGED = 'FLAGGED', 'Flagged'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        RESUBMITTED = 'RESUBMITTED', 'Resubmitted'
        COMMENT_ADDED = 'COMMENT_ADDED', 'Comment Added'
        EXPORTED = 'EXPORTED', 'Exported'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='audit_logs'
    )
    row_id = models.CharField(max_length=100, db_index=True)
    row_source = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=Action.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    source_file = models.CharField(max_length=512, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied("AuditLog records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("AuditLog records cannot be deleted.")

    class Meta:
        ordering = ['-performed_at']

class RowComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='row_comments'
    )
    row_id = models.CharField(max_length=100, db_index=True)
    row_source = models.CharField(max_length=20)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_comments'
    )
    role_at_time = models.CharField(max_length=50)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_finding = models.BooleanField(default=False)
    
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_comments'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            orig = RowComment.objects.get(pk=self.pk)
            if self.body != orig.body or self.is_finding != orig.is_finding or self.author_id != orig.author_id:
                raise PermissionDenied("RowComment body, finding status, and author are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("RowComments cannot be deleted.")

    class Meta:
        ordering = ['created_at']


# ── Emission Factor Registry ──────────────────────────────────────────────────

class EmissionFactor(models.Model):
    """
    Single source of truth for all GHG emission factors.
    Covers Scope 1 (fuel), Scope 2 (electricity), Scope 3 (travel).
    Compliant with: GHG Protocol, IPCC AR6, CEA V20, DEFRA 2024, SEBI BRSR.
    """

    class Scope(models.TextChoices):
        SCOPE_1 = 'SCOPE_1', 'Scope 1 — Direct'
        SCOPE_2 = 'SCOPE_2', 'Scope 2 — Electricity'
        SCOPE_3 = 'SCOPE_3', 'Scope 3 — Value Chain'

    class Source(models.TextChoices):
        CEA_V20          = 'CEA_V20',          'CEA CO2 Baseline Database V20.0'
        IPCC_2006        = 'IPCC_2006',        'IPCC 2006 Guidelines'
        IPCC_AR6         = 'IPCC_AR6',         'IPCC AR6 (2021)'
        DEFRA_2024       = 'DEFRA_2024',       'DEFRA / DESNZ 2024'
        ICAO_2023        = 'ICAO_2023',        'ICAO Carbon Emissions Calculator 2023'
        INDIA_GHG        = 'INDIA_GHG',        'India GHG Program'
        GHG_PROTOCOL     = 'GHG_PROTOCOL',     'GHG Protocol Cross-Sector Tools'

    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope                = models.CharField(max_length=20,  choices=Scope.choices, db_index=True)
    fuel_or_activity_type = models.CharField(max_length=100, db_index=True,
        help_text="e.g. diesel, electricity_india, flight_short_haul, hotel_night")
    factor_value         = models.FloatField()
    factor_unit          = models.CharField(max_length=100,
        help_text="e.g. 'kg CO2e / litre' or 'kg CO2e / kWh'")
    source_name          = models.CharField(max_length=30, choices=Source.choices)
    source_version       = models.CharField(max_length=150, blank=True)
    valid_from_fy        = models.CharField(max_length=10,
        help_text="India FY e.g. '2024-25'")
    valid_to_fy          = models.CharField(max_length=10, null=True, blank=True,
        help_text="null = still current")
    country_code         = models.CharField(max_length=5, default='IN')
    notes                = models.TextField(null=True, blank=True)
    is_active            = models.BooleanField(default=True, db_index=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Emission Factor'
        verbose_name_plural = 'Emission Factors'
        ordering            = ['-valid_from_fy', 'scope', 'fuel_or_activity_type']
        unique_together     = [('scope', 'fuel_or_activity_type', 'valid_from_fy', 'country_code')]
        indexes = [
            models.Index(fields=['scope', 'fuel_or_activity_type', 'is_active']),
        ]

    def __str__(self):
        return (f"[{self.scope}] {self.fuel_or_activity_type} "
                f"= {self.factor_value} {self.factor_unit} "
                f"({self.source_name}, FY {self.valid_from_fy})")

