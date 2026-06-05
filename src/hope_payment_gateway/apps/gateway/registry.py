from django.core.exceptions import ObjectDoesNotExist
from strategy_field.registry import Registry


class FSPProcessor:
    def __init__(self, fsp) -> None:
        self.fsp = fsp

    def label(self) -> str:
        return self.__class__.__name__  # pragma: no-cover

    def notify(self) -> None:
        pass  # pragma: no-cover

    def get_configuration(self, destination_country, delivery_mechanism):
        payload = self.fsp.configuration or {}
        try:
            config = self.fsp.configs.get(
                country=destination_country,
                delivery_mechanism__code=delivery_mechanism,
            ).configuration
            payload["delivery_mechanism"] = delivery_mechanism
            payload.update(config)
        except ObjectDoesNotExist:
            config = self.fsp.configuration
        return config


class DefaultProcessor(FSPProcessor):
    pass


registry = Registry(FSPProcessor)
export_registry = Registry(FSPProcessor)
