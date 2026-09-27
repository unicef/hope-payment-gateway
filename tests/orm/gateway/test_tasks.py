import pytest
from strategy_field.utils import fqn

from factories import PaymentInstructionFactory, PaymentRecordFactory
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.apps.gateway.tasks import cancel_records, collect_payment_records


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
def test_collect_payment_records_without_arguments_returns_every_record():
    expected = PaymentRecordFactory.create_batch(5)

    assert collect_payment_records() == sorted(record.id for record in expected)


@pytest.mark.django_db
def test_collect_payment_records_filters_by_ids():
    expected = PaymentRecordFactory.create_batch(2)
    excluded = PaymentRecordFactory.create_batch(3)

    result = collect_payment_records(ids=[record.id for record in expected])

    assert result == sorted(record.id for record in expected)
    assert not set(result) & {record.id for record in excluded}


@pytest.mark.django_db
def test_collect_payment_records_with_empty_ids_returns_nothing():
    PaymentRecordFactory.create()

    assert collect_payment_records(ids=[]) == []


@pytest.mark.django_db
def test_collect_payment_records_filters_by_single_status():
    transferred = PaymentRecordFactory.create_batch(2, status=PaymentRecordState.TRANSFERRED_TO_FSP)
    PaymentRecordFactory.create_batch(4, status=PaymentRecordState.PENDING)

    result = collect_payment_records(status=PaymentRecordState.TRANSFERRED_TO_FSP)

    assert result == sorted(record.id for record in transferred)


@pytest.mark.django_db
def test_collect_payment_records_filters_by_multiple_statuses():
    pending = PaymentRecordFactory.create_batch(2, status=PaymentRecordState.PENDING)
    transferred = PaymentRecordFactory.create_batch(1, status=PaymentRecordState.TRANSFERRED_TO_FSP)
    PaymentRecordFactory.create_batch(3, status=PaymentRecordState.CANCELLED)

    result = collect_payment_records(status=[PaymentRecordState.PENDING, PaymentRecordState.TRANSFERRED_TO_FSP])

    assert result == sorted(record.id for record in [*pending, *transferred])


@pytest.mark.django_db
def test_collect_payment_records_filters_by_office():
    instruction = PaymentInstructionFactory.create()
    expected = PaymentRecordFactory.create_batch(2, parent=instruction)
    other = PaymentRecordFactory.create_batch(3)

    result = collect_payment_records(office=instruction.office_id)

    assert result == sorted(record.id for record in expected)
    assert not set(result) & {record.id for record in other}


@pytest.mark.django_db
def test_collect_payment_records_filters_by_instruction():
    instruction = PaymentInstructionFactory.create()
    expected = PaymentRecordFactory.create_batch(2, parent=instruction)
    other = PaymentRecordFactory.create_batch(3)

    result = collect_payment_records(instruction=instruction.pk)

    assert result == sorted(record.id for record in expected)
    assert not set(result) & {record.id for record in other}


@pytest.mark.django_db
def test_collect_payment_records_combines_arguments():
    instruction = PaymentInstructionFactory.create()
    expected = PaymentRecordFactory.create_batch(2, parent=instruction, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create(parent=instruction, status=PaymentRecordState.CANCELLED)
    PaymentRecordFactory.create(status=PaymentRecordState.PENDING)

    result = collect_payment_records(
        ids=[record.id for record in expected],
        status=PaymentRecordState.PENDING,
        office=instruction.office_id,
        instruction=instruction.pk,
    )

    assert result == sorted(record.id for record in expected)


@pytest.mark.django_db
def test_collect_payment_records_via_async_job(admin_user):
    instruction = PaymentInstructionFactory.create()
    expected = PaymentRecordFactory.create_batch(2, parent=instruction, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(3, status=PaymentRecordState.CANCELLED)

    job = AsyncJob.objects.create(
        description="Collect payment records",
        type=AsyncJob.JobType.STANDARD_TASK,
        action=collect_payment_records.name,
        owner=admin_user,
        config={"status": PaymentRecordState.PENDING, "instruction": instruction.pk},
    )
    job.queue()

    assert job.execute() == sorted(record.id for record in expected)


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
