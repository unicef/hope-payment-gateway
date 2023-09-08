from django.db.models import Q

from constance import config

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.send_money_complete import (
    send_money_complete,
)
from hope_payment_gateway.celery import app


@app.task()
def send_money(threshold=None, ba=None):
    qs = PaymentRecord.objects.filter(status=PaymentRecord.STATUS_PENDING)
    if ba:
        qs.filter(Q(business_area__slug=ba) | Q(business_area__code=ba))
    for payment_record in qs[: (threshold if threshold else config.WESTERN_UNION_THRESHOLD)]:
        send_money_complete(payment_record.pk)
