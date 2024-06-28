from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import delivery_mechanism_registry, export_registry, registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Western Union"

    def ready(self) -> None:
        from .handlers import WesternUnionHandler

        registry.register(WesternUnionHandler)

        from . import tasks  # noqa
