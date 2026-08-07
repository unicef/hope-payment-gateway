import pytest
from unittest.mock import patch

from factories import PaymentInstructionFactory
from hope_payment_gateway.apps.gateway.models import PaymentInstruction
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp


@pytest.mark.django_db
def test_handler_calls_trigger_event_with_correct_payload():
    pi = PaymentInstructionFactory()

    with patch("hope_payment_gateway.apps.bitcaster.handlers.trigger_event") as mock_trigger:
        payment_instruction_sent_to_fsp.send(sender=PaymentInstruction, instance=pi)

    mock_trigger.assert_called_once_with(
        "payment_instruction_sent_to_fsp",
        {
            "pk": pi.pk,
            "external_code": pi.external_code,
            "fsp": str(pi.fsp),
            "status": pi.status,
        },
    )
