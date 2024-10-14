import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .. import env

SENTRY_DSN = env("SENTRY_DSN")

if SENTRY_DSN:  # pragma: no cover
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # by default this is False, must be set to True so the library attaches the request data to the event
        send_default_pii=True,
        enable_tracing=True,
        integrations=[DjangoIntegration(), CeleryIntegration(), LoggingIntegration()],
        environment=env("SENTRY_ENVIRONMENT"),
    )
