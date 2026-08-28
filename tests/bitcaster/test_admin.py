from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin import site
from django.contrib.messages import WARNING
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from factories import SuperUserFactory, UserFactory
from hope_payment_gateway.apps.bitcaster.admin import BitcasterUserAdminMixin, sync_to_bitcaster
from hope_payment_gateway.apps.bitcaster.client import HopeBitcasterClient
from hope_payment_gateway.apps.core.admin import UserAdminPlus
from hope_payment_gateway.apps.core.models import User


@pytest.fixture
def admin_instance():
    return UserAdminPlus(User, site)


@pytest.fixture
def admin_request(db):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = SuperUserFactory()
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


@pytest.mark.django_db
@pytest.mark.parametrize(
    "enabled, expected_in_actions",
    [
        (False, False),
        (True, True),
    ],
)
def test_sync_action_visibility(admin_instance, admin_request, settings, enabled, expected_in_actions):
    settings.BITCASTER_ENABLED = enabled
    actions = admin_instance.get_actions(admin_request)
    assert ("sync_to_bitcaster" in actions) is expected_in_actions


@pytest.mark.django_db
def test_sync_action_calls_register_user_per_user(admin_instance, admin_request):
    users = [UserFactory() for _ in range(3)]
    queryset = User.objects.filter(pk__in=[u.pk for u in users])
    mock_client = MagicMock(spec=HopeBitcasterClient)

    with patch("hope_payment_gateway.apps.bitcaster.admin.get_hope_bitcaster_client", return_value=mock_client):
        sync_to_bitcaster(admin_instance, admin_request, queryset)

    assert mock_client.register_user.call_count == 3


@pytest.mark.django_db
def test_sync_action_shows_success_message(admin_instance, admin_request):
    users = [UserFactory(), UserFactory()]
    queryset = User.objects.filter(pk__in=[u.pk for u in users])
    mock_client = MagicMock(spec=HopeBitcasterClient)

    with patch("hope_payment_gateway.apps.bitcaster.admin.get_hope_bitcaster_client", return_value=mock_client):
        sync_to_bitcaster(admin_instance, admin_request, queryset)

    storage = list(admin_request._messages)
    assert len(storage) == 1
    assert "2" in storage[0].message
    assert "Bitcaster" in storage[0].message


@pytest.mark.django_db
def test_sync_action_shows_warning_when_client_not_configured(admin_instance, admin_request):
    users = [UserFactory()]
    queryset = User.objects.filter(pk__in=[u.pk for u in users])

    with patch("hope_payment_gateway.apps.bitcaster.admin.get_hope_bitcaster_client", return_value=None):
        sync_to_bitcaster(admin_instance, admin_request, queryset)

    storage = list(admin_request._messages)
    assert len(storage) == 1
    assert storage[0].level == WARNING


def test_bitcaster_mixin_is_applied():
    assert issubclass(UserAdminPlus, BitcasterUserAdminMixin)
