import pytest
from unittest.mock import patch

from factories import UserFactory
from hope_payment_gateway.apps.bitcaster.tasks import sync_user_to_bitcaster, unregister_user_from_bitcaster


@pytest.mark.django_db
def test_sync_task_returns_silently_for_missing_user():
    sync_user_to_bitcaster(999999)


@pytest.mark.django_db
def test_sync_task_calls_register_member_for_active_user(bitcaster_settings):
    user = UserFactory(is_active=True)
    with patch("hope_payment_gateway.apps.bitcaster.tasks.register_member") as mock_register:
        sync_user_to_bitcaster(user.pk)
    mock_register.assert_called_once_with(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=True,
    )


@pytest.mark.django_db
def test_sync_task_passes_inactive_flag(bitcaster_settings):
    user = UserFactory(is_active=False)
    with patch("hope_payment_gateway.apps.bitcaster.tasks.register_member") as mock_register:
        sync_user_to_bitcaster(user.pk)
    mock_register.assert_called_once_with(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=False,
    )


@pytest.mark.django_db
def test_sync_task_propagates_errors():
    user = UserFactory()
    with patch(
        "hope_payment_gateway.apps.bitcaster.tasks.register_member",
        side_effect=ConnectionError("timeout"),
    ):
        with pytest.raises(ConnectionError):
            sync_user_to_bitcaster(user.pk)


def test_unregister_task_calls_unregister_member(bitcaster_settings):
    with patch("hope_payment_gateway.apps.bitcaster.tasks.unregister_member") as mock_unregister:
        unregister_user_from_bitcaster("demo-user")
    mock_unregister.assert_called_once_with("demo-user")


def test_unregister_task_propagates_errors():
    with patch(
        "hope_payment_gateway.apps.bitcaster.tasks.unregister_member",
        side_effect=ConnectionError("timeout"),
    ):
        with pytest.raises(ConnectionError):
            unregister_user_from_bitcaster("demo-user")
