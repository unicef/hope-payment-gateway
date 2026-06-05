import pytest
from constance.test import override_config

from hope_payment_gateway.apps.fsp.palpay.handlers import PalPayHandler
from tests.factories.payment import CountryFactory


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_payload(palpay):
    destination_country = CountryFactory(iso_code2="US")
    code = "code"
    PalPayHandler(palpay).get_configuration(destination_country, code)
