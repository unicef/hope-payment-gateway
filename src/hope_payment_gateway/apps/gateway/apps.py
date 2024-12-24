from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Gateway"

    def ready(self) -> None:
        from hope_payment_gateway.apps.fsp.western_union.handlers import WesternUnionHandler

        registry.register(WesternUnionHandler)
