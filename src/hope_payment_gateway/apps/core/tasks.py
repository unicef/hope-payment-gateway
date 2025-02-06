import contextlib
import logging
from typing import TYPE_CHECKING, Any

import sentry_sdk
from django.core.cache import cache
from redis_lock import Lock

from hope_payment_gateway.apps.gateway.models import AsyncJob
from hope_payment_gateway.config.celery import app

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from redis_lock.django_cache import RedisCache

    cache: RedisCache


@contextlib.contextmanager
def lock_job(job: AsyncJob) -> Lock:
    lock = None
    if job.group_key:
        lock_key = f"lock:{job.group_key}"
        # Get a lock with a 60-second lifetime but keep renewing it automatically
        # to ensure the lock is held for as long as the Python process is running.
        lock = cache.lock(lock_key, 60, auto_renewal=True)
        yield lock.__enter__()
    else:
        yield
    if lock:
        lock.release()


@app.task()
def sync_job_task(pk: int, version: int) -> dict[str, Any]:
    try:
        job: AsyncJob = AsyncJob.objects.select_related("owner").get(pk=pk, version=version)
    except AsyncJob.DoesNotExist as e:
        sentry_sdk.capture_exception(e)
        raise e

    with lock_job(job):
        try:
            scope = sentry_sdk.get_current_scope()
            if job.owner:
                sentry_sdk.set_user = {"id": job.owner.pk, "email": job.owner.email}
            return job.execute()
        except Exception:
            # error is logged in job.execute
            raise
        finally:
            scope.clear()


@app.task()
def removed_expired_jobs(**kwargs):
    AsyncJob.objects.filter(**kwargs).delete()
