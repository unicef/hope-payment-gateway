from django.dispatch import receiver

from hope_payment_gateway.apps.bitcaster.client import trigger_event
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp


@receiver(payment_instruction_sent_to_fsp)
def handle_payment_instruction_sent_to_fsp(sender, **kwargs):
    pi = sender  # sender is a PaymentInstruction instance
    trigger_event(
        "payment_instruction_sent_to_fsp",
        {
            "pk": pi.pk,
            "external_code": pi.external_code,
            "fsp": str(pi.fsp),
            "status": pi.status,
        },
    )
