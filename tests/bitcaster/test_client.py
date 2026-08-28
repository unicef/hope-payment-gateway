import logging
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from hope_payment_gateway.apps.bitcaster.client import (
    HopeBitcasterClient,
    get_hope_bitcaster_client,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    HopeBitcasterClient.reset()
    yield
    HopeBitcasterClient.reset()


def test_get_client_disabled():
    assert get_hope_bitcaster_client() is None


def test_get_client_missing_bae_returns_none_and_logs_warning(bitcaster_settings, caplog):
    bitcaster_settings.BITCASTER_BAE = ""

    with caplog.at_level(logging.WARNING):
        result = get_hope_bitcaster_client()

    assert result is None
    assert "Bitcaster not fully configured" in caplog.text


def test_get_client_returns_instance(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.client.import_string") as mock_import:
        mock_import.return_value = MagicMock(return_value=MagicMock())
        result = get_hope_bitcaster_client()

    assert isinstance(result, HopeBitcasterClient)


def test_get_client_caches_singleton(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.client.import_string") as mock_import:
        mock_class = MagicMock(return_value=MagicMock())
        mock_import.return_value = mock_class

        first = get_hope_bitcaster_client()
        second = get_hope_bitcaster_client()

    assert first is second
    mock_class.assert_called_once()


def test_get_client_constructs_sdk_with_correct_args(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.client.import_string") as mock_import:
        mock_class = MagicMock(return_value=MagicMock())
        mock_import.return_value = mock_class

        get_hope_bitcaster_client()

    mock_class.assert_called_once_with(
        bae="https://testkey@bitcaster.example.com/api/o/org/",
        project="project",
        application="app",
    )


@pytest.mark.django_db
def test_register_user_calls_sdk_with_email_address(bitcaster_settings):
    from factories import UserFactory

    user = UserFactory(email="u@example.com", first_name="Alice", last_name="Smith", is_active=True)
    mock_sdk = MagicMock()
    mock_sdk.register_user.return_value = {"created": True}
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.register_user(user)

    mock_sdk.register_user.assert_called_once_with(
        project="project",
        application="app",
        username=user.username,
        email="u@example.com",
        first_name="Alice",
        last_name="Smith",
        active=True,
        addresses=[{"value": "u@example.com"}],
    )


@pytest.mark.django_db
def test_register_user_is_fire_and_forget():
    from factories import UserFactory

    user = UserFactory()
    mock_sdk = MagicMock()
    mock_future = MagicMock(spec=Future)
    mock_sdk.register_user.return_value = mock_future
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.register_user(user)

    mock_future.result.assert_not_called()


def test_unregister_user_calls_sdk():
    mock_sdk = MagicMock()
    mock_sdk.unregister_user.return_value = {"deleted": 1}
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.unregister_user("demo-user")

    mock_sdk.unregister_user.assert_called_once_with(
        project="project",
        application="app",
        username="demo-user",
    )


def test_unregister_user_is_fire_and_forget():
    mock_sdk = MagicMock()
    mock_future = MagicMock(spec=Future)
    mock_sdk.unregister_user.return_value = mock_future
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.unregister_user("demo-user")

    mock_future.result.assert_not_called()


def test_trigger_event_calls_sdk():
    mock_sdk = MagicMock()
    mock_sdk.trigger_event.return_value = MagicMock()
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.trigger_event("payment_instruction_sent_to_fsp", {"pk": 1})

    mock_sdk.trigger_event.assert_called_once_with("payment_instruction_sent_to_fsp", context={"pk": 1})


def test_trigger_event_no_warning_when_future_not_done():
    mock_sdk = MagicMock()
    mock_sdk.trigger_event.return_value = Future()
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    client.trigger_event("some_event", {})


def test_trigger_event_logs_on_failure(caplog):
    mock_sdk = MagicMock()
    future = Future()
    future.set_exception(Exception("something went wrong"))
    mock_sdk.trigger_event.return_value = future
    client = HopeBitcasterClient(mock_sdk, project="project", application="app")

    with caplog.at_level(logging.WARNING):
        client.trigger_event("some_event", {})

    assert "Bitcaster event dropped (queue full)" in caplog.text
    assert "some_event" in caplog.text
