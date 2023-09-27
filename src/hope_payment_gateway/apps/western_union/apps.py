from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.western_union.registry import registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Western Union"

    def ready(self) -> None:
        from hope_payment_gateway.apps.western_union.handlers.western_union import WesternUnionHandler

        registry.register(WesternUnionHandler)
