from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = "hope_payment_gateway.apps.bitcaster"
    verbose_name = "Bitcaster"

    def ready(self) -> None:
        from . import handlers  # noqa