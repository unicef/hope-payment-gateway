import os
import tempfile

from django.core.management import call_command

import pytest

from tests import factories


def pytest_sessionstart(session):
    from django.test import TestCase

    TestCase.multi_db = True
    TestCase.databases = "__all__"

    from django.apps import apps

    models = apps.get_app_config("hope").get_models()
    for model in models:
        model._meta.managed = True


def pytest_configure(config):
    os.environ["TESTING"] = "1"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
    os.environ["STATIC_ROOT"] = tempfile.gettempdir()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "hope.json", "--database=hope")


@pytest.fixture()
def user(request, db):
    return factories.UserFactory()


@pytest.fixture()
def logged_user(client, user):
    client.force_authenticate(user)
    return user


@pytest.fixture()
def business_area():
    return factories.BusinessAreaFactory()


@pytest.fixture()
def fsp():
    return factories.FinancialServiceProviderFactory()


@pytest.fixture()
def payment():
    return factories.PaymentFactory()


@pytest.fixture()
def payment_plan():
    return factories.PaymentPlanFactory()


@pytest.fixture()
def programme():
    return factories.ProgrammeFactory()
