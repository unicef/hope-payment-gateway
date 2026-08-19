from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from hope_payment_gateway.apps.bitcaster.client import trigger_event
from hope_payment_gateway.apps.bitcaster.tasks import sync_user_to_bitcaster, unregister_user_from_bitcaster
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp

if TYPE_CHECKING:  # pragma: no cover
    from hope_payment_gateway.apps.gateway.models import PaymentInstruction


@receiver(payment_instruction_sent_to_fsp)
def handle_payment_instruction_sent_to_fsp(sender: type, instance: PaymentInstruction, **kwargs: Any) -> None:
    pi = instance
    trigger_event(
        "payment_instruction_sent_to_fsp",
        {
            "pk": pi.pk,
            "external_code": pi.external_code,
            "fsp": str(pi.fsp),
            "status": pi.status,
        },
    )


@receiver(post_save, sender=get_user_model())
def handle_user_saved(sender: type, instance: Any, **kwargs: Any) -> None:
    sync_user_to_bitcaster.delay(instance.pk)


@receiver(pre_delete, sender=get_user_model())
def handle_user_deleted(sender: type, instance: Any, **kwargs: Any) -> None:
    # NOTE: QuerySet.delete() bypasses per-instance signals, so bulk deletions
    # (e.g. admin "delete selected", management commands) will NOT unregister
    # affected users from Bitcaster.
    unregister_user_from_bitcaster.delay(instance.username)
