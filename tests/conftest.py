import os
import tempfile

import pytest

from .factories import CorridorFactory, PaymentInstructionFactory, PaymentRecordLogFactory, UserFactory


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
    return PaymentRecordLogFactory()
