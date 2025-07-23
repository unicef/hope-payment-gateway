from django.apps import AppConfig as BaseAppConfig

from hope_payment_gateway.apps.gateway.registry import registry


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "MoneyGram"

    def ready(self) -> None:
        from .handlers import MoneyGramHandler  # noqa

        registry.register(MoneyGramHandler)
        from . import tasks  # noqa
