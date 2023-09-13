import os
import tempfile

import pytest

from tests import factories


def pytest_configure(config):
    os.environ["TESTING"] = "1"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
    os.environ["STATIC_ROOT"] = tempfile.gettempdir()


@pytest.fixture()
def user(request, db):
    return factories.UserFactory()


@pytest.fixture()
def logged_user(client, user):
    client.force_authenticate(user)
    return user


@pytest.fixture()
def corridor():
    return factories.CorridorFactory()
