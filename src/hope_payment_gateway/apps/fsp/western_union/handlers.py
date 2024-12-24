from constance import config as constance_config

from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, FinancialServiceProviderConfig
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    @staticmethod
    def get_configuration(config_key, delivery_mechanism):
        vendor_number = constance_config.WESTERN_UNION_VENDOR_NUMBER
        wu = FinancialServiceProvider.objects.get(vendor_number=vendor_number)
        payload = wu.configuration
        try:
            fsp = FinancialServiceProviderConfig.objects.get(
                key=config_key, fsp=wu, delivery_mechanism__code=delivery_mechanism
            )

            payload.update(fsp.configuration)
            payload["delivery_mechanism"] = fsp.delivery_mechanism.code
        except FinancialServiceProviderConfig.DoesNotExist:
            pass
        return payload


class CSVExportStrategy(FSPProcessor):
    def export(self):
        pass
