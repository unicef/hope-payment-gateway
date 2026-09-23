from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentRecordState


def cancel_records(ids: list[int] | None = None) -> None:
    records = PaymentRecord.objects.filter(
        id__in=ids or [],
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    for record in records:
        PaymentRecordFlow(record).cancel()
