from django.db.models import Q

from constance import config

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.send_money import send_money
from hope_payment_gateway.celery import app


@app.task()
def send_money_task(threshold=config.WESTERN_UNION_THREASHOLD, ba=None):
    qs = PaymentRecord.objects.filter(status=PaymentRecord.STATUS_PENDING)
    if ba:
        qs.filter(Q(business_area__slug=ba) | Q(business_area__code=ba))
    for payment_record in qs[:threshold]:
        send_money(payment_record.pk)
