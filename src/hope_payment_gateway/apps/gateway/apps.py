from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import delivery_mechanism_registry, export_registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Gateway"

    def ready(self) -> None:

        from .handlers import CSVExportStrategy, MobileMoneyProcessor

        export_registry.register(CSVExportStrategy)
        delivery_mechanism_registry.register(MobileMoneyProcessor)
