import logging
from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver
from flags.state import flag_enabled

from hope_payment_gateway.apps.gateway.models import PaymentInstruction, PaymentRecord
from hope_payment_gateway.apps.stream.handlers import (
    notify_instruction_change,
    notify_record_change,
)

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PaymentInstruction)
def instruction_updated(sender: Any, instance: PaymentInstruction, **kwargs: dict) -> None:
    if flag_enabled("ENABLE_STREAMING") and instance.pk:
        try:
            old_instance = PaymentInstruction.objects.get(pk=instance.pk)
        except PaymentInstruction.DoesNotExist:
            old_instance = None

        if old_instance and old_instance.status != instance.status:
            logger.info(f"Status changed: {old_instance.status} → {instance.status}")
            notify_instruction_change(instance.pk, instance.status)


@receiver(pre_save, sender=PaymentRecord)
def record_updated(sender: Any, instance: PaymentRecord, **kwargs: Any) -> None:
    if flag_enabled("ENABLE_STREAMING") and instance.pk:
        try:
            old_instance = PaymentRecord.objects.get(pk=instance.pk)
        except PaymentRecord.DoesNotExist:
            old_instance = None

        if old_instance and old_instance.status != instance.status:
            logger.info(f"Status changed: {old_instance.status} → {instance.status}")
            notify_record_change(instance.pk, instance.status)
