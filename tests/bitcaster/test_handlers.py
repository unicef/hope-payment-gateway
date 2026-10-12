from unittest.mock import MagicMock, patch

import pytest

from hope_bitcaster.client import HopeBitcasterClient
from hope_payment_gateway.apps.gateway.models import PaymentInstruction
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp


@pytest.mark.django_db
def test_payment_handler_calls_trigger_event_with_correct_payload(pi):
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.handlers.get_hope_bitcaster_client", return_value=mock_client):
        payment_instruction_sent_to_fsp.send(sender=PaymentInstruction, instance=pi)

    mock_client.trigger_event.assert_called_once_with(
        "payment_instruction_sent_to_fsp",
        {
            "pk": pi.pk,
            "external_code": pi.external_code,
            "fsp": str(pi.fsp),
            "status": pi.status,
        },
    )


@pytest.mark.django_db
def test_payment_handler_is_no_op_when_client_is_none(pi):
    with patch("hope_payment_gateway.apps.bitcaster.handlers.get_hope_bitcaster_client", return_value=None):
        payment_instruction_sent_to_fsp.send(sender=PaymentInstruction, instance=pi)
