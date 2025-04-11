from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.fsp.palpay.client import PalPayClient
from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp, send_to_fsp
from hope_payment_gateway.apps.gateway.models import (
    PaymentRecord,
)
from hope_payment_gateway.config.celery import app


def palpay_notify(to_process_ids: list[PaymentRecord]) -> None:
    notify_records_to_fsp(fqn(PalPayClient), to_process_ids)


@app.task()  # queue="executors"
def palpay_send_money(tag=None, threshold=10000):
    """Task to trigger PalPay payments."""
    fsp = "PalPay"
    fsp_vendor_number = config.PALPAY_VENDOR_NUMBER
    threshold = threshold or config.PALPAY_THREASHOLD
    action_fqn = palpay_notify
    group_key = "pal-send-instruction"

    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key, threshold, tag)
