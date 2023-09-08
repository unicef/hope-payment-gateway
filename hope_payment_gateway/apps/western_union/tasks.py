from django.db.models import Q

from constance import config

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.send_money_complete import (
    send_money_complete,
)
from hope_payment_gateway.config.celery import app


@app.task()
def send_money(threshold=None, business_area=None):
    qs = PaymentRecord.objects.filter(status=PaymentRecord.STATUS_PENDING)
    if business_area:
        qs.filter(Q(business_area__slug=business_area) | Q(business_area__code=business_area))
    for payment_record in qs[: (threshold if threshold else config.WESTERN_UNION_THRESHOLD)]:
        send_money_complete(payment_record.pk)
