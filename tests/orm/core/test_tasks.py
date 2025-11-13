from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from hope_payment_gateway.apps.core.tasks import sync_job_task, removed_expired_jobs
from hope_payment_gateway.apps.gateway.models import AsyncJob

from tests.factories import PaymentInstructionFactory, UserFactory
from tests.factories.tasks import AsyncJobFactory


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.gateway.models.AsyncJob.execute")
@patch("sentry_sdk.get_current_scope")
@patch("sentry_sdk.capture_exception")
def test_sync_job_task_success(mocked_capture_exception, mocked_get_current_scope, mocked_execute):
    user = UserFactory()
    job = AsyncJobFactory(owner=user, group_key=None)

    scope = MagicMock()
    scope.clear.return_value = None
    mocked_get_current_scope.return_value = scope

    mocked_execute.return_value = None

    sync_job_task(job.pk, job.version)

    mocked_capture_exception.assert_not_called()
    scope.clear.assert_called_once()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.gateway.models.AsyncJob.execute")
@patch("sentry_sdk.get_current_scope")
@patch("sentry_sdk.capture_exception")
def test_sync_job_task_fail(mocked_capture_exception, mocked_get_current_scope, mocked_execute):
    user = UserFactory()
    job = AsyncJobFactory(owner=user, group_key=None)

    scope = MagicMock()
    scope.clear.return_value = None
    mocked_get_current_scope.return_value = scope

    mocked_execute.side_effect = Exception()  # noqa: B017, PT011

    with pytest.raises(Exception):  # noqa: B017, PT011
        sync_job_task(job.pk, job.version)

    mocked_capture_exception.assert_not_called()
    scope.clear.assert_called_once()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.gateway.models.AsyncJob.execute")
@patch("sentry_sdk.get_current_scope")
@patch("sentry_sdk.capture_exception")
def test_sync_job_task_success_without_owner(mocked_capture_exception, mocked_get_current_scope, mocked_execute):
    job = AsyncJobFactory(group_key=None)

    scope = MagicMock()
    scope.clear.return_value = None
    mocked_get_current_scope.return_value = scope

    mocked_execute.return_value = None

    sync_job_task(job.pk, job.version)

    mocked_capture_exception.assert_not_called()
    scope.clear.assert_called_once()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("sentry_sdk.capture_exception")
def test_sync_job_task_not_found(mock_sentry):
    with pytest.raises(AsyncJob.DoesNotExist):
        sync_job_task(999, 1)

    assert mock_sentry.call_count == 1
    assert isinstance(mock_sentry.call_args[0][0], AsyncJob.DoesNotExist)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_removed_expired_jobs():
    # create payment instruction instances to assert deletion against them
    pi_1 = PaymentInstructionFactory.create()
    pi_2 = PaymentInstructionFactory.create()

    AsyncJobFactory.create_batch(3, instruction=pi_1)
    AsyncJobFactory.create_batch(2, instruction=pi_2)

    removed_expired_jobs(instruction=pi_1)

    assert AsyncJob.objects.filter(instruction_id=pi_1.pk).count() == 0
    assert AsyncJob.objects.filter(instruction_id=pi_2.pk).count() == 2
