import logging
from concurrent.futures import Future
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils.module_loading import import_string

if TYPE_CHECKING:  # pragma: no cover
    from django.contrib.auth.base_user import AbstractBaseUser
    from bitcaster_sdk.abstract_client import AbstractClient

logger = logging.getLogger(__name__)


class HopeBitcasterClient:
    _instance: "HopeBitcasterClient | None" = None

    def __init__(self, sdk_client: "AbstractClient", project: str, application: str) -> None:
        self._client = sdk_client
        self._project = project
        self._application = application

    @classmethod
    def from_settings(cls) -> "HopeBitcasterClient | None":
        bae = settings.BITCASTER_BAE
        project = settings.BITCASTER_PROJECT_SLUG
        application = settings.BITCASTER_APPLICATION_SLUG
        if not all([bae, project, application]):
            logger.warning("Bitcaster not fully configured — notifications disabled")
            return None
        client_class = import_string(settings.BITCASTER_CLIENT_CLASS)
        sdk_client = client_class(bae=bae, project=project, application=application)
        return cls(sdk_client=sdk_client, project=project, application=application)

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register_user(self, user: "AbstractBaseUser") -> None:
        self._client.register_user(
            project=self._project,
            application=self._application,
            username=user.username,
            email=user.email,
            first_name=getattr(user, "first_name", "") or "",
            last_name=getattr(user, "last_name", "") or "",
            active=user.is_active,
            addresses=[{"value": user.email}],
        )

    def unregister_user(self, username: str) -> None:
        self._client.unregister_user(
            project=self._project,
            application=self._application,
            username=username,
        )

    def trigger_event(self, event_name: str, payload: dict[str, Any]) -> None:
        result = self._client.trigger_event(event_name, context=payload)
        if isinstance(result, Future) and result.done() and result.exception():
            logger.warning("Bitcaster event dropped (queue full): %s", event_name)


def get_hope_bitcaster_client() -> "HopeBitcasterClient | None":
    if HopeBitcasterClient._instance is not None:
        return HopeBitcasterClient._instance
    if not settings.BITCASTER_ENABLED:
        return None
    client = HopeBitcasterClient.from_settings()
    HopeBitcasterClient._instance = client
    return client
