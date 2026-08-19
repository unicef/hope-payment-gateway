import logging
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from hope_payment_gateway.apps.bitcaster.client import (
    _state,
    get_client,
    register_member,
    trigger_event,
    unregister_member,
)


@pytest.fixture(autouse=True)
def reset_client_state():
    _state["client"] = None
    yield
    _state["client"] = None


def test_get_client_disabled():
    assert get_client() is None


def test_get_client_missing_setting_returns_none_and_logs_warning(bitcaster_settings, caplog):
    bitcaster_settings.BITCASTER_BAE = ""

    with caplog.at_level(logging.WARNING):
        result = get_client()

    assert result is None
    assert "Bitcaster not fully configured" in caplog.text


def test_get_client_returns_async_client(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.client.import_string") as mock_import:
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_import.return_value = mock_class

        result = get_client()

        assert result is mock_instance
        mock_class.assert_called_once_with(
            bae="https://testkey@bitcaster.example.com/api/o/org/",
            project="project",
            application="app",
        )


def test_get_client_caches_singleton(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.client.import_string") as mock_import:
        mock_class = MagicMock()
        mock_class.return_value = MagicMock()
        mock_import.return_value = mock_class

        first = get_client()
        second = get_client()

        assert first is second
        mock_class.assert_called_once()


def test_trigger_event_skips_when_no_client():
    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=None):
        trigger_event("some_event", {"key": "value"})


def test_trigger_event_calls_client():
    mock_client = MagicMock()
    mock_future = MagicMock()
    mock_client.trigger_event.return_value = mock_future

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        trigger_event("payment_instruction_sent_to_fsp", {"pk": 1})

    mock_client.trigger_event.assert_called_once_with("payment_instruction_sent_to_fsp", context={"pk": 1})


def test_trigger_event_no_warning_when_future_not_done():
    mock_client = MagicMock()
    mock_future = MagicMock()
    mock_future.done.return_value = False
    mock_client.trigger_event.return_value = mock_future

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        trigger_event("some_event", {})

    mock_future.exception.assert_not_called()


def test_trigger_event_logs_on_failure(caplog):
    mock_client = MagicMock()
    mock_future = MagicMock()
    mock_future.done.return_value = True
    mock_future.exception.return_value = Exception("something went wrong")
    mock_client.trigger_event.return_value = mock_future

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING):
            trigger_event("some_event", {})

    assert "Bitcaster event dropped (queue full)" in caplog.text
    assert "some_event" in caplog.text


def test_register_member_skips_when_no_client():
    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=None):
        register_member("user", "u@example.com", "First", "Last")


def test_register_member_calls_sdk(bitcaster_settings):
    mock_client = MagicMock()
    mock_client.register_user.return_value = {"created": True}

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        register_member("user", "u@example.com", "First", "Last", True)

    mock_client.register_user.assert_called_once_with(
        project="project",
        application="app",
        username="user",
        email="u@example.com",
        first_name="First",
        last_name="Last",
        active=True,
    )


def test_register_member_blocks_on_future():
    mock_client = MagicMock()
    mock_future = MagicMock(spec=Future)
    mock_client.register_user.return_value = mock_future

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        register_member("user", "u@example.com", "First", "Last")

    mock_future.result.assert_called_once()


def test_unregister_member_skips_when_no_client():
    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=None):
        unregister_member("user")


def test_unregister_member_calls_sdk(bitcaster_settings):
    mock_client = MagicMock()
    mock_client.unregister_user.return_value = {"deleted": 1}

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        unregister_member("user")

    mock_client.unregister_user.assert_called_once_with(
        project="project",
        application="app",
        username="user",
    )


def test_unregister_member_blocks_on_future():
    mock_client = MagicMock()
    mock_future = MagicMock(spec=Future)
    mock_client.unregister_user.return_value = mock_future

    with patch("hope_payment_gateway.apps.bitcaster.client.get_client", return_value=mock_client):
        unregister_member("user")

    mock_future.result.assert_called_once()
