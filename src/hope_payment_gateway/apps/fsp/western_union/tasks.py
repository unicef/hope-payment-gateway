from constance import config

from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord
from hope_payment_gateway.celery import app


@app.task
def western_union_send_task(vision_vendor_number, tag=None, threshold=config.DEFAULT_THREASHOLD):
    wu = FinancialServiceProvider.objects.get(vision_vendor_number=vision_vendor_number)

    records = PaymentRecord.objects.none()
    qs = PaymentInstruction.objects.filter(status=PaymentInstruction.READY, fsp=wu)
    if tag:
        qs = qs.filter(tag=tag)
    for pi in qs:
        new_records = pi.paymentrecord_set.filter(status=PaymentRecord.PENDING)
        if len(list(records)) + new_records.count() >= threshold:
            new_records = new_records[: threshold - len(list(records))]
            records = records | new_records
            break
        records = records | new_records

    wu.strategy.notify(records)