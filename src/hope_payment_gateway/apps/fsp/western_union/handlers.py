from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, FinancialServiceProviderConfig
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):

    def get_configuration(self, config_key, delivery_mechanism):
        wu = FinancialServiceProvider.objects.get(vendor_number="1900723202")
        try:
            fsp = FinancialServiceProviderConfig.objects.get(
                key=config_key, fsp=wu, delivery_mechanism__code=delivery_mechanism
            )
        except FinancialServiceProviderConfig.DoesNotExist:
            fsp = wu.config
        config = fsp.configuration
        config["delivery_mechanism"] = fsp.delivery_mechanism.code
        return config


class CSVExportStrategy(FSPProcessor):

    def export(self):
        pass
