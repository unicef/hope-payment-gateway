from ..settings import env

CELERY_ACCEPT_CONTENT = ["pickle", "json", "application/text"]
CELERY_BROKER_URL = env("CACHE_URL")
CELERY_BROKER_VISIBILITY_VAR = env("CELERY_VISIBILITY_TIMEOUT", default=1800)  # in seconds
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": int(CELERY_BROKER_VISIBILITY_VAR)}
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
# Sensible settings for celery
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False
CELERY_TASK_IGNORE_RESULT = True
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_RESULT_EXPIRES = 600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {"hope_payment_gateway.apps.fsp.western_union.tasks.western_union_notify": {"queue": "executors"}}
