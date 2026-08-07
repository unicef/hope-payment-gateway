import logging
from typing import Any
from urllib.parse import urlparse

from bitcaster_sdk.async_client import AsyncClient
from django.conf import settings

logger = logging.getLogger(__name__)

_state: dict[str, AsyncClient | None] = {"client": None}


def _build_bae(api_url: str, api_key: str, organization_slug: str) -> str:
    parsed = urlparse(api_url)
    return f"{parsed.scheme}://{api_key}@{parsed.netloc}/api/o/{organization_slug}/"


def get_client() -> AsyncClient | None:
    if _state["client"] is not None:
        return _state["client"]
    if not getattr(settings, "BITCASTER_ENABLED", False):
        return None
    api_url = settings.BITCASTER_API_URL
    api_key = settings.BITCASTER_API_KEY
    org = settings.BITCASTER_ORGANIZATION_SLUG
    project = settings.BITCASTER_PROJECT_SLUG
    application = settings.BITCASTER_APPLICATION_SLUG
    if not all([api_url, api_key, org, project, application]):
        logger.warning("Bitcaster not fully configured — notifications disabled")
        return None
    _state["client"] = AsyncClient(
        bae=_build_bae(api_url, api_key, org),
        project=project,
        application=application,
    )
    return _state["client"]


def trigger_event(event_name: str, payload: dict[str, Any]) -> None:
    client = get_client()
    if client is None:
        return
    future = client.trigger_event(event_name, context=payload)

    def _on_done(f):
        if f.exception():
            logger.warning("Bitcaster event failed: %s — %s", event_name, f.exception())

    future.add_done_callback(_on_done)
