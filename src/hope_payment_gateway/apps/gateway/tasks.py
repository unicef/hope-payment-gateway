from __future__ import annotations

from typing import TYPE_CHECKING

from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentRecordState
from hope_payment_gateway.config.celery import app

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence


@app.task()
def collect_payment_records(
    ids: Sequence[int] | None = None,
    status: str | Sequence[str] | None = None,
    office: int | None = None,
    instruction: int | None = None,
) -> list[int]:
    """Return the primary keys of the matching payment records.

    Every argument narrows the records to select and is ignored when `None`, so a call without
    arguments collects every payment record. It is meant to be run periodically (an hourly
    `IntervalSchedule` created in the django-celery-beat admin is a sensible default) and can also be
    queued manually or through an `AsyncJob`, whose `config` maps straight onto the arguments.

    Arguments:
        ids: The `PaymentRecord` primary keys to match.
        status: A single `PaymentRecordState` or a collection of them.
        office: The `Office` primary key of the parent `PaymentInstruction` to match.
        instruction: The `PaymentInstruction` primary key to match.

    Returns:
        The primary keys of the matching `PaymentRecord` rows, ordered by id.

    """
    records = PaymentRecord.objects.all()
    if ids is not None:
        records = records.filter(pk__in=ids)
    if status is not None:
        records = records.filter(status__in=[status] if isinstance(status, str) else status)
    if office is not None:
        records = records.filter(parent__office=office)
    if instruction is not None:
        records = records.filter(parent=instruction)
    return list(records.order_by("id").values_list("id", flat=True))


def cancel_records(ids: list[int] | None = None) -> None:
    records = PaymentRecord.objects.filter(
        id__in=ids or [],
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    for record in records:
        PaymentRecordFlow(record).cancel()
