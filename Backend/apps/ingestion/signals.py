"""
apps/ingestion/signals.py
==========================
Django signals for:
1. AuditLog creation on every row status change.
2. AUTO CO2 CALCULATION — fires after every row save where
   status=PENDING and co2e_kg is null.
3. CO2 COMPARISON + AUTO-FLAGGING — if a document CO2 claim
   diverges > 15% from system calculation, auto-flags the row
   and creates an AuditLog + RowComment.
"""

import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.emissions.models import SAPRow, UtilityRow, TravelRow
from apps.ingestion.models import AuditLog, RowComment

logger = logging.getLogger(__name__)


# ── 1. Capture previous status before save ─────────────────────────────────────

@receiver(pre_save, sender=SAPRow)
@receiver(pre_save, sender=UtilityRow)
@receiver(pre_save, sender=TravelRow)
def capture_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._previous_status = old.status
            instance._previous_co2    = old.co2e_kg
        except sender.DoesNotExist:
            instance._previous_status = None
            instance._previous_co2    = None
    else:
        instance._previous_status = None
        instance._previous_co2    = None


# ── 2. AuditLog on status change ───────────────────────────────────────────────

@receiver(post_save, sender=SAPRow)
@receiver(post_save, sender=UtilityRow)
@receiver(post_save, sender=TravelRow)
def create_audit_log_on_status_change(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_previous_status', None)

    if not created and previous_status == instance.status:
        pass  # fall through — still run CO2 calculation below
    else:
        action_map = {
            'PENDING':      AuditLog.Action.INGESTED if created else AuditLog.Action.RESUBMITTED,
            'FLAGGED':      AuditLog.Action.FLAGGED,
            'APPROVED':     AuditLog.Action.APPROVED,
            'REJECTED':     AuditLog.Action.REJECTED,
            'LOCKED':       AuditLog.Action.EXPORTED,
            'PARSE_FAILED': AuditLog.Action.FLAGGED,
        }
        action      = action_map.get(instance.status, AuditLog.Action.FLAGGED)
        source_name = sender.__name__.replace('Row', '').upper()
        performed_by = getattr(instance, '_performed_by',
                               getattr(instance, '_audit_user', None))
        try:
            AuditLog.objects.create(
                organisation    = instance.organisation,
                row_id          = str(instance.id),
                row_source      = source_name,
                action          = action,
                previous_status = previous_status,
                new_status      = instance.status,
                note            = getattr(
                    instance, '_audit_note',
                    f"Row ingested with status {instance.status}" if created
                    else f"Status changed to {instance.status}"
                ),
                performed_by    = performed_by,
            )
        except Exception as e:
            logger.error("Failed to create AuditLog: %s", e)

    # ── 3. Auto CO2 calculation ──────────────────────────────────────────────
    _trigger_co2_calculation(sender, instance, created)


def _trigger_co2_calculation(sender, instance, created):
    """
    Fire the CO2 engine when:
    - Row is PENDING
    - co2e_kg is still null (not already calculated)
    - Never recalculate APPROVED / LOCKED rows
    """
    if instance.status not in ('PENDING', 'FLAGGED'):
        return
    if instance.co2e_kg is not None:
        return  # already calculated — don't recalculate

    try:
        from core.utils.co2_calculator import calculate_from_row, compare_co2, EmissionFactorNotFound
        result = calculate_from_row(instance)
    except EmissionFactorNotFound as e:
        logger.warning("CO2 calc — no factor found for row %s: %s", instance.pk, e)
        # Mark row as PARSE_FAILED with informative error
        sender.objects.filter(pk=instance.pk).update(
            status      = 'PARSE_FAILED',
            parse_error = str(e),
        )
        return
    except Exception as e:
        logger.error("CO2 calc error on row %s: %s", instance.pk, e)
        return

    # Build the update dict — never touch status here
    update_fields = {
        'co2e_kg':                   result['co2e_kg'],
        'ghg_scope':                 result.get('ghg_scope'),
        'ghg_category':              result.get('ghg_category'),
        'emission_factor_value':     result.get('emission_factor_value'),
        'emission_factor_unit':      result.get('emission_factor_unit'),
        'emission_factor_source':    result.get('emission_factor_source'),
        'emission_factor_year':      result.get('emission_factor_year'),
        'emission_factor_record_id': result.get('emission_factor_record_id'),
        'formula':                   result.get('formula'),
    }

    # For UtilityRow / SAPRow: run document vs system comparison
    if hasattr(instance, 'document_claimed_co2_kg'):
        doc_co2 = instance.document_claimed_co2_kg
        sys_co2 = result['co2e_kg']

        comparison = compare_co2(doc_co2, sys_co2)
        update_fields['system_calculated_co2_kg'] = sys_co2
        update_fields['co2_variance_pct']          = comparison.get('variance_pct')
        update_fields['co2_comparison_status']     = comparison['status']

        if comparison['status'] == 'MAJOR_VARIANCE':
            update_fields['status'] = 'FLAGGED'
            _create_major_variance_flag(instance, doc_co2, sys_co2,
                                         comparison['variance_pct'], result)

    # Use update() to avoid re-triggering the signal
    sender.objects.filter(pk=instance.pk).update(**update_fields)
    logger.info(
        "CO2 auto-calculated: row=%s co2e=%.4f kg formula=%s",
        instance.pk, result['co2e_kg'], result.get('formula', '')
    )


def _get_system_user():
    """Return (or create) a system service account for automated actions."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username='system',
        defaults={
            'email':     'system@breatheesg.internal',
            'is_active': False,
            'first_name': 'BreatheESG',
            'last_name':  'System',
        }
    )
    return user


def _create_major_variance_flag(instance, doc_co2, sys_co2, variance_pct, result):
    """
    When document CO2 diverges > 15% from system calculation:
    - Create AuditLog entry (action=FLAGGED, performed_by=None=system)
    - Create RowComment as a finding
    """
    source_name = type(instance).__name__.replace('Row', '').upper()
    factor_src  = result.get('emission_factor_source', '')
    factor_val  = result.get('emission_factor_value', '')
    factor_unit = result.get('emission_factor_unit', '')

    audit_note = (
        f"AUTO-FLAGGED: Document claims {doc_co2:.2f} kg CO2e but system calculated "
        f"{sys_co2:.2f} kg CO2e (variance: {variance_pct:.1f}%). "
        f"Requires analyst review before audit approval."
    )
    comment_body = (
        f"CO2 discrepancy detected. Document states {doc_co2:.2f} kg CO2e; "
        f"system calculated {sys_co2:.2f} kg CO2e using {factor_src} factor "
        f"({factor_val} {factor_unit}). "
        f"Variance: {variance_pct:.1f}%. Analyst must verify source document before approving."
    )

    try:
        AuditLog.objects.create(
            organisation    = instance.organisation,
            row_id          = str(instance.id),
            row_source      = source_name,
            action          = AuditLog.Action.FLAGGED,
            previous_status = instance.status,
            new_status      = 'FLAGGED',
            note            = audit_note,
            performed_by    = None,   # system action
        )
    except Exception as e:
        logger.error("Failed to create major-variance AuditLog: %s", e)

    try:
        system_user = _get_system_user()
        RowComment.objects.create(
            organisation  = instance.organisation,
            row_id        = str(instance.id),
            row_source    = source_name,
            author        = system_user,
            role_at_time  = 'SYSTEM',
            body          = comment_body,
            is_finding    = True,
        )
    except Exception as e:
        logger.error("Failed to create major-variance RowComment: %s", e)
