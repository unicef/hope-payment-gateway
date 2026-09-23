import pytest
from strategy_field.utils import fqn

from factories import PaymentRecordFactory
from hope_payment_gateway.apps.gateway.models import AsyncJob, PaymentRecord, PaymentRecordState
from hope_payment_gateway.apps.gateway.tasks import cancel_records


@pytest.mark.django_db
def test_cancel_records_only_cancels_transferred_to_fsp():
    transferred = PaymentRecordFactory.create_batch(2, status=PaymentRecordState.TRANSFERRED_TO_FSP)
    pending = PaymentRecordFactory.create(status=PaymentRecordState.PENDING)
    ids = [record.id for record in [*transferred, pending]]

    cancel_records(ids=ids)

    for record in transferred:
        record.refresh_from_db()
        assert record.status == PaymentRecordState.CANCELLED
    pending.refresh_from_db()
    assert pending.status == PaymentRecordState.PENDING


@pytest.mark.django_db
def test_cancel_records_with_empty_ids():
    cancel_records(ids=[])

    assert PaymentRecord.objects.count() == 0


@pytest.mark.django_db
def test_cancel_records_via_async_job(admin_user):
    transferred = PaymentRecordFactory.create_batch(2, status=PaymentRecordState.TRANSFERRED_TO_FSP)
    job = AsyncJob.objects.create(
        description="Cancel payment records",
        type=AsyncJob.JobType.STANDARD_TASK,
        owner=admin_user,
        action=fqn(cancel_records),
        config={"ids": [record.id for record in transferred]},
    )

    job.execute()

    for record in transferred:
        record.refresh_from_db()
        assert record.status == PaymentRecordState.CANCELLED
