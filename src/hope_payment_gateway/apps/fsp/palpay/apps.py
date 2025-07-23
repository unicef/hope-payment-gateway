from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "PalPay"

    def ready(self) -> None:
        from .handlers import PalPayHandler  # noqa

        registry.register(PalPayHandler)
        from . import tasks  # noqa
