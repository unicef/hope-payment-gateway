from constance import config

from hope_payment_gateway.apps.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord
from hope_payment_gateway.celery import app


@app.task
def send_money_task():
    records = PaymentRecord.objects.none()
    qs = PaymentInstruction.objects.filter(status=PaymentInstruction.READY)
    for pi in qs:
        new_records = pi.paymentrecord_set.filter(status=PaymentRecord.PENDING)
        if len(list(records)) + new_records.count() >= config.WESTERN_UNION_THREASHOLD:
            new_records = new_records[: config.WESTERN_UNION_THREASHOLD - len(list(records))]
            records = records | new_records
            break
        records = records | new_records

    for record in records:
        send_money(record.get_payload())
