import logging
from concurrent.futures import Future
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils.module_loading import import_string

if TYPE_CHECKING:  # pragma: no cover
    from bitcaster_sdk.abstract_client import AbstractClient

logger = logging.getLogger(__name__)

_state: dict[str, AbstractClient | None] = {"client": None}


def get_client() -> AbstractClient | None:
    if _state["client"] is not None:
        return _state["client"]
    if not settings.BITCASTER_ENABLED:
        return None
    bae = settings.BITCASTER_BAE
    org = settings.BITCASTER_ORGANIZATION_SLUG
    project = settings.BITCASTER_PROJECT_SLUG
    application = settings.BITCASTER_APPLICATION_SLUG
    if not all([bae, org, project, application]):
        logger.warning("Bitcaster not fully configured — notifications disabled")
        return None
    client_class = import_string(settings.BITCASTER_CLIENT_CLASS)
    _state["client"] = client_class(
        bae=bae,
        project=project,
        application=application,
    )
    return _state["client"]


def trigger_event(event_name: str, payload: dict[str, Any]) -> None:
    client = get_client()
    if client is None:
        return
    future = client.trigger_event(event_name, context=payload)
    if future.done() and future.exception():
        logger.warning("Bitcaster event dropped (queue full): %s", event_name)


def register_member(
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    is_active: bool = True,
) -> None:
    client = get_client()
    if client is None:
        return
    result = client.register_user(
        project=settings.BITCASTER_PROJECT_SLUG,
        application=settings.BITCASTER_APPLICATION_SLUG,
        username=username,
        email=email,
        first_name=first_name or "",
        last_name=last_name or "",
        active=is_active,
    )
    if isinstance(result, Future):
        result.result()


def unregister_member(username: str) -> None:
    client = get_client()
    if client is None:
        return
    result = client.unregister_user(
        project=settings.BITCASTER_PROJECT_SLUG,
        application=settings.BITCASTER_APPLICATION_SLUG,
        username=username,
    )
    if isinstance(result, Future):
        result.result()
