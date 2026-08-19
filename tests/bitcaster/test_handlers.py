import pytest
from unittest.mock import patch

from factories import UserFactory
from hope_payment_gateway.apps.gateway.models import PaymentInstruction
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp


@pytest.mark.django_db
def test_handler_calls_trigger_event_with_correct_payload(pi):
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


@pytest.mark.django_db
def test_user_save_enqueues_sync_task():
    with patch("hope_payment_gateway.apps.bitcaster.handlers.sync_user_to_bitcaster") as mock_task:
        user = UserFactory()
        user.first_name = "Updated"
        user.save()

    mock_task.delay.assert_any_call(user.pk)


@pytest.mark.django_db
def test_user_delete_enqueues_unregister_task():
    user = UserFactory()
    username = user.username
    with patch("hope_payment_gateway.apps.bitcaster.handlers.unregister_user_from_bitcaster") as mock_task:
        user.delete()

    mock_task.delay.assert_called_once_with(username)
