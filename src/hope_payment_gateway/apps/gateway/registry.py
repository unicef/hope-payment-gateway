import logging

from django.core.exceptions import ObjectDoesNotExist
from strategy_field.registry import Registry

logger = logging.getLogger(__name__)


class FSPProcessor:
    def __init__(self, fsp) -> None:
        self.fsp = fsp

    def label(self) -> str:
        return self.__class__.__name__  # pragma: no-cover

    def notify(self) -> None:
        pass  # pragma: no-cover

    def get_configuration(self, destination_country, delivery_mechanism):
        """Retrieve FSP configuration for a given country and delivery mechanism.

        Falls back to the base FSP configuration if no country-specific config exists.
        """
        payload = dict(self.fsp.configuration or {})
        try:
            config = self.fsp.configs.get(
                country=destination_country,
                delivery_mechanism__code=delivery_mechanism,
            ).configuration
            payload["delivery_mechanism"] = delivery_mechanism
            payload["destination_country"] = destination_country.iso_code2
            payload.update(config or {})
        except ObjectDoesNotExist:
            logger.warning(
                "No FSP config found for %s / %s, using base configuration",
                self.fsp,
                destination_country,
            )
        return payload


class DefaultProcessor(FSPProcessor):
    pass


registry = Registry(FSPProcessor)
export_registry = Registry(FSPProcessor)
