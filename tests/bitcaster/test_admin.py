from unittest.mock import patch

import pytest
from django.contrib.admin import site
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from factories import SuperUserFactory, UserFactory
from hope_payment_gateway.apps.core.admin import UserAdminPlus, sync_to_bitcaster
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
    messages = FallbackStorage(request)
    request._messages = messages
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
def test_sync_action_enqueues_task_per_user(admin_instance, admin_request):
    users = [UserFactory() for _ in range(3)]
    queryset = User.objects.filter(pk__in=[u.pk for u in users])

    with patch("hope_payment_gateway.apps.core.admin.sync_user_to_bitcaster") as mock_task:
        sync_to_bitcaster(admin_instance, admin_request, queryset)

    assert mock_task.delay.call_count == 3
    called_pks = {call.args[0] for call in mock_task.delay.call_args_list}
    assert called_pks == {u.pk for u in users}


@pytest.mark.django_db
def test_sync_action_shows_success_message(admin_instance, admin_request):
    users = [UserFactory(), UserFactory()]
    queryset = User.objects.filter(pk__in=[u.pk for u in users])

    with patch("hope_payment_gateway.apps.core.admin.sync_user_to_bitcaster"):
        sync_to_bitcaster(admin_instance, admin_request, queryset)

    storage = list(admin_request._messages)
    assert len(storage) == 1
    assert "2" in storage[0].message
    assert "Bitcaster" in storage[0].message
