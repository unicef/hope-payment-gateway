from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from hope_payment_gateway.apps.bitcaster.client import get_hope_bitcaster_client
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp

if TYPE_CHECKING:  # pragma: no cover
    from hope_payment_gateway.apps.gateway.models import PaymentInstruction


# --- generic handlers (library-bound) ---
@receiver(post_save, sender=get_user_model())
def handle_user_saved(sender: type, instance: Any, **kwargs: Any) -> None:
    client = get_hope_bitcaster_client()
    if client is None:
        return
    client.register_user(instance)


@receiver(pre_delete, sender=get_user_model())
def handle_user_deleted(sender: type, instance: Any, **kwargs: Any) -> None:
    # NOTE: QuerySet.delete() bypasses per-instance signals, so bulk deletions
    # (e.g. admin "delete selected", management commands) will NOT unregister
    # affected users from Bitcaster.
    client = get_hope_bitcaster_client()
    if client is None:
        return
    client.unregister_user(instance.username)


# --- payment-gateway-specific handlers (stays in this repo) ---
@receiver(payment_instruction_sent_to_fsp)
def handle_payment_instruction_sent_to_fsp(sender: type, instance: "PaymentInstruction", **kwargs: Any) -> None:
    client = get_hope_bitcaster_client()
    if client is None:
        return
    client.trigger_event(
        "payment_instruction_sent_to_fsp",
        {
            "pk": instance.pk,
            "external_code": instance.external_code,
            "fsp": str(instance.fsp),
            "status": instance.status,
        },
    )
