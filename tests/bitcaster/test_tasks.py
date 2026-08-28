from unittest.mock import MagicMock, patch

import pytest
from factories import UserFactory

from hope_payment_gateway.apps.bitcaster.client import HopeBitcasterClient
from hope_payment_gateway.apps.bitcaster.tasks import sync_user_to_bitcaster, unregister_user_from_bitcaster


@pytest.mark.django_db
def test_sync_task_returns_silently_when_client_not_configured():
    sync_user_to_bitcaster(999999)


@pytest.mark.django_db
def test_sync_task_returns_silently_for_missing_user(bitcaster_settings):
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.tasks.get_hope_bitcaster_client", return_value=mock_client):
        sync_user_to_bitcaster(999999)

    mock_client.register_user.assert_not_called()


@pytest.mark.django_db
def test_sync_task_calls_register_user(bitcaster_settings):
    user = UserFactory()
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.tasks.get_hope_bitcaster_client", return_value=mock_client):
        sync_user_to_bitcaster(user.pk)

    mock_client.register_user.assert_called_once_with(user)


@pytest.mark.django_db
def test_sync_task_propagates_errors(bitcaster_settings):
    user = UserFactory()
    mock_client = MagicMock(spec=HopeBitcasterClient)
    mock_client.register_user.side_effect = ConnectionError("timeout")
    with patch("hope_payment_gateway.apps.bitcaster.tasks.get_hope_bitcaster_client", return_value=mock_client):
        with pytest.raises(ConnectionError):
            sync_user_to_bitcaster(user.pk)


def test_unregister_task_returns_silently_when_client_not_configured():
    unregister_user_from_bitcaster("demo-user")


def test_unregister_task_calls_unregister_user(bitcaster_settings):
    mock_client = MagicMock(spec=HopeBitcasterClient)
    with patch("hope_payment_gateway.apps.bitcaster.tasks.get_hope_bitcaster_client", return_value=mock_client):
        unregister_user_from_bitcaster("demo-user")

    mock_client.unregister_user.assert_called_once_with("demo-user")


def test_unregister_task_propagates_errors(bitcaster_settings):
    mock_client = MagicMock(spec=HopeBitcasterClient)
    mock_client.unregister_user.side_effect = ConnectionError("timeout")
    with patch("hope_payment_gateway.apps.bitcaster.tasks.get_hope_bitcaster_client", return_value=mock_client):
        with pytest.raises(ConnectionError):
            unregister_user_from_bitcaster("demo-user")
