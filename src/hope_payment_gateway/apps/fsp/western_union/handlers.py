from hope_payment_gateway.apps.fsp.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, FinancialServiceProviderConfig
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    def notify(self, records):
        for record in records:
            send_money(record.get_payload())

    def get_configuration(self, config_key):
        wu = FinancialServiceProvider.objects.get(vision_vendor_number="1900723202")
        try:
            config = FinancialServiceProviderConfig.objects.get(key=config_key, fsp=wu).configuration
        except FinancialServiceProviderConfig.DoesNotExist:
            config = wu.configuration
        return config
