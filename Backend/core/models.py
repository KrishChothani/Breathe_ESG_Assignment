from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    """
    Abstract base for every model that holds tenant-specific data.
    Extending this ensures every subclass has an `organisation` FK and
    timestamps. The TenantQuerysetMixin (core/mixins.py) filters by this field
    automatically on every request.
    """
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True
