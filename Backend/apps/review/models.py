import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ReviewAction(models.Model):
    """
    Immutable audit log of every analyst decision on a normalised data row.

    Uses a GenericForeignKey so that a single ReviewAction table can reference
    SAPRow, UtilityRow, or TravelRow without a union table per source type.
    Each action is append-only — rows are never mutated here; the status field
    on the target row is updated as a side-effect of the action.
    """
    class Action(models.TextChoices):
        APPROVE = 'APPROVE', 'Approve'
        REJECT = 'REJECT', 'Reject'
        LOCK = 'LOCK', 'Lock for auditor'
        FLAG = 'FLAG', 'Flag for further review'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Generic FK — points to any NormalisedRow subclass
    row_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name='review_actions'
    )
    row_object_id = models.UUIDField(db_index=True)
    row = GenericForeignKey('row_content_type', 'row_object_id')

    analyst = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='review_actions',
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review Action'
        verbose_name_plural = 'Review Actions'
        indexes = [
            models.Index(fields=['row_content_type', 'row_object_id']),
        ]

    def __str__(self):
        return f"[{self.action}] by {self.analyst} at {self.created_at:%Y-%m-%d %H:%M}"
