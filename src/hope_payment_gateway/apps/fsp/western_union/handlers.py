from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, FinancialServiceProviderConfig
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):

    def get_configuration(self, config_key, delivery_mechanism):
        wu = FinancialServiceProvider.objects.get(vision_vendor_number="1900723202")
        try:
            config = FinancialServiceProviderConfig.objects.get(
                key=config_key, fsp=wu, delivery_mechanism__code=delivery_mechanism
            ).configuration
        except FinancialServiceProviderConfig.DoesNotExist:
            config = wu.configuration
        return config


class CSVExportStrategy(FSPProcessor):

    def export(self):
        pass
