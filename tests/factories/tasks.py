from factory import Faker
from hope_payment_gateway.apps.gateway.models import AsyncJob

from tests.factories import AutoRegisterModelFactory


class AsyncJobFactory(AutoRegisterModelFactory):
    description = Faker("sentence")
    type = AsyncJob.JobType.STANDARD_TASK
    action = Faker("word")
    config = Faker("pydict", value_types=["str", "int", "float", "bool"])
    group_key = Faker("word")
    owner = None
    version = 0
    curr_async_result_id = None
    last_async_result_id = None
    datetime_queued = None
    repeatable = False
    celery_history = {}
    local_status = ""
    sentry_id = None

    class Meta:
        model = AsyncJob
