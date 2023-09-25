import os
import tempfile

import pytest

from hope_api_auth.models import Grant

from .factories import APITokenFactory, CorridorFactory, PaymentInstructionFactory, PaymentRecordFactory, UserFactory


def pytest_configure(config):
    os.environ["TESTING"] = "1"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
    os.environ["STATIC_ROOT"] = tempfile.gettempdir()


@pytest.fixture(autouse=True)
def use_override_settings(settings):
    settings.WESTERN_UNION_BASE_URL = "https://wugateway2pi.westernunion.com/"


@pytest.fixture()
def user(request, db):
    return UserFactory()


@pytest.fixture()
def logged_user(client, user):
    client.force_authenticate(user)
    return user


@pytest.fixture()
def corridor():
    return CorridorFactory()


@pytest.fixture()
def pi():
    return PaymentInstructionFactory()


@pytest.fixture()
def prl():
    return PaymentRecordFactory()


@pytest.fixture()
def token_user(admin_user):
    user_permissions = [
        Grant.API_READ_ONLY,
        Grant.API_PLAN_UPLOAD,
        Grant.API_PLAN_MANAGE,
    ]
    APITokenFactory(
        user=admin_user,
        grants=[c.name for c in user_permissions],
    )
    return admin_user


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_client_with_credentials(db, token_user, api_client):
    token = token_user.apitoken_set.first()
    api_client.force_authenticate(user=token_user, token=token)
    yield api_client
    api_client.force_authenticate(user=None)
