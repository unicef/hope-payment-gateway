import pytest
from constance.test import override_config

from hope_payment_gateway.apps.fsp.moneygram.handlers import MoneyGramHandler
from tests.factories.payment import CountryFactory


@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_payload(mg):
    destination_country = CountryFactory(iso_code2="US")
    code = "code"
    MoneyGramHandler(mg).get_configuration(destination_country, code)
