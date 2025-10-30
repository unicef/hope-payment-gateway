from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Streaming"

    def ready(self) -> None:
        super().ready()
        from streaming.manager import initialize_engine  # noqa

        initialize_engine()
