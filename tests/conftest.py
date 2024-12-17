import os
import tempfile

import pytest
import responses
from factories import (
    APITokenFactory,
    CorridorFactory,
    FinancialServiceProviderFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    UserFactory,
)
from strategy_field.utils import fqn

from hope_api_auth.models import Grant
from hope_payment_gateway.apps.fsp.moneygram.handlers import MoneyGramHandler
from hope_payment_gateway.apps.fsp.western_union.handlers import WesternUnionHandler


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


@pytest.fixture(autouse=True)
def use_override_settings(settings):
    settings.WESTERN_UNION_BASE_URL = "https://wugateway2pi.westernunion.com/"
    settings.MONEYGRAM_PARTNER_ID = "AAAAAA"
    settings.MONEYGRAM_HOST = "https://sandboxapi.moneygram.com"
    settings.SECRET_KEY = "6311bc92d3d1ebf12ae2aa54d8aaeeafa9e8cdb4"


@pytest.fixture()
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


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


@pytest.fixture()
def mg():
    return FinancialServiceProviderFactory(
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


@pytest.fixture()
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
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_client_with_credentials(db, token_user, api_client):
    token = token_user.apitoken_set.first()
    api_client.force_authenticate(user=token_user, token=token)
    yield api_client
    api_client.force_authenticate(user=None)
