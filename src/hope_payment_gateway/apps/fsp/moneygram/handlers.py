from constance import config as constance_config

from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
)
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class MoneyGramHandler(FSPProcessor):
    @staticmethod
    def get_configuration(config_key, delivery_mechanism):
        vendor_number = constance_config.MONEYGRAM_VENDOR_NUMBER
        wu = FinancialServiceProvider.objects.get(vendor_number=vendor_number)
        try:
            config = FinancialServiceProviderConfig.objects.get(
                key=config_key, fsp=wu, delivery_mechanism__code=delivery_mechanism
            ).configuration
        except FinancialServiceProviderConfig.DoesNotExist:
            config = wu.configuration
        return config
