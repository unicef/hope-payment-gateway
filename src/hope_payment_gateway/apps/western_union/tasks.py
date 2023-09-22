from itertools import chain

from constance import config

from hope_payment_gateway.apps.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord


def send_money_task():
    records = PaymentRecord.objects.none()
    qs = PaymentInstruction.objects.filter(status=PaymentInstruction.READY)
    for pi in qs:
        new_records = pi.paymentrecordlog_set.filter(status=PaymentRecord.PENDING)
        if len(records) + new_records.count() >= config.WESTERN_UNION_THREASHOLD:
            new_records = new_records[: config.WESTERN_UNION_THREASHOLD - len(records)]
            records = chain(records, new_records)
            break
        records = chain(records, new_records)

    for record in records:
        send_money(record.get_payload())
