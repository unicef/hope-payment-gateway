from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

from hope_bitcaster.client import get_hope_bitcaster_client
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp

if TYPE_CHECKING:  # pragma: no cover
    from hope_payment_gateway.apps.gateway.models import PaymentInstruction


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
