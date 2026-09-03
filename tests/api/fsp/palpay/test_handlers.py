import pytest
from constance.test import override_config
from factories import CountryFactory

from hope_payment_gateway.apps.fsp.palpay.handlers import PalPayHandler


@pytest.fixture
def us_country():
    return CountryFactory.create(iso_code2="US")


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_payload(palpay, us_country):
    code = "code"
    PalPayHandler(palpay).get_configuration(us_country, code)
