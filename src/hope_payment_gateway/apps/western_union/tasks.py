from constance import config

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.send_money_complete import send_money_complete
from hope_payment_gateway.celery import app


@app.task()
def send_money(threshold=config.WESTERN_UNION_THREASHOLD):
    qs = PaymentRecord.objects.filter(status=PaymentRecord.STATUS_PENDING)
    for payment_record in qs[:threshold]:
        send_money_complete(payment_record.pk)
