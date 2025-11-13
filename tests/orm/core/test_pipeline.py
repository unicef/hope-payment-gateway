from django.test import override_settings
import pytest

from hope_payment_gateway.apps.core.pipeline import set_superusers
from tests.factories import UserFactory


SUPERUSER_EMAIL = "superuser@example.com"


@pytest.fixture
def superuser_user(request, db):
    return UserFactory(email=SUPERUSER_EMAIL)


@pytest.mark.django_db
@override_settings(SUPERUSERS=[SUPERUSER_EMAIL])
def test_set_superusers_with_new_user(superuser_user):
    res = set_superusers(user=superuser_user, is_new=True)

    superuser_user.refresh_from_db()
    assert superuser_user.is_superuser is True
    assert res == {}


@pytest.mark.django_db
@override_settings(SUPERUSERS=[SUPERUSER_EMAIL])
def test_set_superusers_with_not_new_user(superuser_user):
    res = set_superusers(user=superuser_user, is_new=False)

    assert superuser_user.is_superuser is False
    assert res == {}


@pytest.mark.django_db
@override_settings(SUPERUSERS=[SUPERUSER_EMAIL])
def test_set_superusers_with_new_random_user(user):
    res = set_superusers(user=user, is_new=False)

    assert user.is_superuser is False
    assert res == {}


@override_settings(SUPERUSERS=[SUPERUSER_EMAIL])
def test_set_superusers_with_no_user():
    res = set_superusers(user=None, is_new=True)
    assert res == {}
