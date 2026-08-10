from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

from hope_payment_gateway.apps.bitcaster.client import trigger_event
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
