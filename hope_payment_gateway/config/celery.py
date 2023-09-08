import logging
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hope_payment_gateway.config.settings")

logger = logging.getLogger(__name__)

app = Celery("sir")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
