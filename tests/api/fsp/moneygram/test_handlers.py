import pytest
from constance.test import override_config

from hope_payment_gateway.apps.fsp.moneygram.handlers import MoneyGramHandler


@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_payload(mg):
    config_key = "config_key"
    code = "code"
    MoneyGramHandler(mg).get_configuration(config_key, code)
