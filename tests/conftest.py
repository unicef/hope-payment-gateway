import os
import tempfile

import pytest
import responses
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from hope_api_auth.models import Grant
from hope_payment_gateway.apps.fsp.moneygram.handlers import MoneyGramHandler
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.handlers import WesternUnionHandler
from strategy_field.utils import fqn
from unittest.mock import MagicMock
from factories import (
    APITokenFactory,
    CorridorFactory,
    FinancialServiceProviderFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    UserFactory,
    FinancialServiceProviderConfigFactory,
    DeliveryMechanismFactory,
)
from rest_framework.test import APIClient

from django.contrib.admin import ModelAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord


def pytest_configure(config):
    os.environ["TESTING"] = "1"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
    os.environ["STATIC_ROOT"] = tempfile.gettempdir()
    os.environ["CSRF_COOKIE_SECURE"] = "0"
    os.environ["SECURE_SSL_REDIRECT"] = "0"
    os.environ["SESSION_COOKIE_HTTPONLY"] = "0"
    os.environ["SESSION_COOKIE_SECURE"] = "0"
    os.environ["DEFAULT_FROM_EMAIL"] = "test@email.org"
    os.environ["SECRET_KEY"] = "6311bc92d3d1ebf12ae2aa54d8aaeeafa9e8cdb4"
    config.addinivalue_line("markers", "smoke: mark test as part of the smoke test suite")
    config.addinivalue_line("markers", "skip_models(*models): skip test for specified model names")
    config.addinivalue_line(
        "markers", "skip_buttons(*buttons): skip test for specified admin buttons, format: 'app.ModelAdmin:button_name'"
    )
    config.addinivalue_line("markers", "admin: mark test as part of the admin test suite")


@pytest.fixture(autouse=True)
def use_override_settings(settings):
    settings.WESTERN_UNION_BASE_URL = "https://wugateway2pi.westernunion.com/"
    settings.MONEYGRAM_HOST = "https://sandboxapi.moneygram.com"
    settings.SECRET_KEY = "6311bc92d3d1ebf12ae2aa54d8aaeeafa9e8cdb4"


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def user(request, db):
    return UserFactory()


@pytest.fixture
def logged_user(client, user):
    client.force_authenticate(user)
    return user


@pytest.fixture
def corridor():
    return CorridorFactory()


@pytest.fixture
def pi():
    return PaymentInstructionFactory()


@pytest.fixture
def prl():
    return PaymentRecordFactory()


@pytest.fixture
def wu():
    return FinancialServiceProviderFactory(
        name="Western Union",
        vendor_number="12345",
        strategy=fqn(WesternUnionHandler),
        configuration={
            "sender": {
                "name": {
                    "name_type": "C",
                    "business_name": "BUSINESS",
                },
                "address": {
                    "addr_line1": "Piazza della liberta",
                    "addr_line2": "",
                    "city": "NEW YORK",
                    "state": "NY",
                    "postal_code": "10000",
                    "country_code": {
                        "iso_code": {
                            "country_code": "US",
                            "currency_code": "USD",
                        },
                        "country_name": "US",
                    },
                    "local_area": "NEW YORK",
                    "street": "Piazza della liberta",
                },
                "email": "email@email.org",
                "contact_phone": "6001234000",
                "mobile_phone": {
                    "phone_number": {
                        "country_code": "1",
                        "national_number": "6001234000",
                    },
                },
                "fraud_warning_consent": "Y",
            },
            "channel": {"type": "H2H", "name": "CHANNEL", "version": "9500"},
        },
    )


@pytest.fixture
def mg():
    mg = FinancialServiceProviderFactory(
        name="MoneyGram",
        vendor_number="67890",
        strategy=fqn(MoneyGramHandler),
        configuration={
            "business": {
                "businessName": "Business",
                "legalEntityName": "Entity",
                "businessType": "ACCOMMODATION_HOTELS",
                "businessRegistrationNumber": "10-2030405",
                "businessIssueDate": "2013-05-26",
                "businessCountryOfRegistration": "USA",
                "address": {
                    "line1": "Piazza della Liberta",
                    "city": "ROME",
                    "countrySubdivisionCode": "US-NY",
                    "countryCode": "USA",
                    "postalCode": 10001,
                },
                "contactDetails": {"phone": {"number": 2003004000, "countryDialCode": 1}},
            }
        },
    )
    dm = DeliveryMechanismFactory(code="money")
    FinancialServiceProviderConfigFactory(
        key="mg-key", fsp=mg, delivery_mechanism=dm, configuration={"agent_partner_id": "agent_partner_id"}
    )

    return mg


@pytest.fixture
def token_user():
    user = UserFactory()
    user_permissions = [
        Grant.API_READ_ONLY,
        Grant.API_PLAN_UPLOAD,
        Grant.API_PLAN_MANAGE,
    ]
    token = APITokenFactory(
        user=user,
        grants=[c.name for c in user_permissions],
    )
    return user, f"Token {token.key}"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_client_with_credentials(db, token_user, api_client):
    token = token_user.apitoken_set.first()
    api_client.force_authenticate(user=token_user, token=token)
    yield api_client
    api_client.force_authenticate(user=None)


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def modeladmin():
    admin = MagicMock(spec=ModelAdmin)
    admin.model = PaymentRecord
    admin.opts = MagicMock()
    admin.opts.verbose_name_plural = "Payment Records"
    admin.opts.app_label = "gateway"
    admin.admin_site = MagicMock()
    admin.admin_site.name = "admin"
    admin.admin_site.each_context.return_value = {}
    admin.get_fieldsets.return_value = []
    return admin


@pytest.fixture
def wu_client():
    return WesternUnionClient()
