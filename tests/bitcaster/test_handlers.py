from unittest.mock import MagicMock, patch

import pytest
from factories import UserFactory

from hope_payment_gateway.apps.bitcaster.client import HopeBitcasterClient
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


@pytest.mark.django_db
def test_user_save_calls_register_user_directly():
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.handlers.get_hope_bitcaster_client", return_value=mock_client):
        user = UserFactory()

    mock_client.register_user.assert_called_with(user)


@pytest.mark.django_db
def test_user_delete_calls_unregister_user_directly():
    user = UserFactory()
    username = user.username
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.handlers.get_hope_bitcaster_client", return_value=mock_client):
        user.delete()

    mock_client.unregister_user.assert_called_once_with(username)


@pytest.mark.django_db
def test_user_handlers_are_no_ops_when_client_is_none():
    with patch("hope_payment_gateway.apps.bitcaster.handlers.get_hope_bitcaster_client", return_value=None):
        user = UserFactory()
        user.delete()
