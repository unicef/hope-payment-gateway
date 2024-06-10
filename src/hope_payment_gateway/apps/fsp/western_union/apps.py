from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import export_registry, registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Western Union"

    def ready(self) -> None:
        from .handlers import CSVExportStrategy, WesternUnionHandler

        registry.register(WesternUnionHandler)
        export_registry.register(CSVExportStrategy)
        from . import tasks  # noqa
