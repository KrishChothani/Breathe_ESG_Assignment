import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.emissions.models import SAPRow, UtilityRow, TravelRow
from apps.ingestion.models import AuditLog

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SAPRow)
@receiver(pre_save, sender=UtilityRow)
@receiver(pre_save, sender=TravelRow)
def capture_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

@receiver(post_save, sender=SAPRow)
@receiver(post_save, sender=UtilityRow)
@receiver(post_save, sender=TravelRow)
def create_audit_log_on_status_change(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_previous_status', None)
    
    if not created and previous_status == instance.status:
        return
        
    action_map = {
        'PENDING': AuditLog.Action.INGESTED if created else AuditLog.Action.RESUBMITTED,
        'FLAGGED': AuditLog.Action.FLAGGED,
        'APPROVED': AuditLog.Action.APPROVED,
        'REJECTED': AuditLog.Action.REJECTED,
        'LOCKED': AuditLog.Action.EXPORTED,
        'PARSE_FAILED': AuditLog.Action.FLAGGED,
    }
    
    action = action_map.get(instance.status, AuditLog.Action.FLAGGED)
    source_name = sender.__name__.replace('Row', '').upper()
    performed_by = getattr(instance, '_performed_by', getattr(instance, '_audit_user', None))

    try:
        AuditLog.objects.create(
            organisation=instance.organisation,
            row_id=str(instance.id),
            row_source=source_name,
            action=action,
            previous_status=previous_status,
            new_status=instance.status,
            note=getattr(instance, '_audit_note', f"Status changed to {instance.status}" if not created else f"Row ingested with status {instance.status}"),
            performed_by=performed_by,
        )
    except Exception as e:
        logger.error("Failed to create AuditLog: %s", e)
