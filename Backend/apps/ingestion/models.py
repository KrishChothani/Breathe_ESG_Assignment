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
