from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.fsp.tasks_utils import send_to_fsp, notify_records_to_fsp
from hope_payment_gateway.apps.gateway.models import (
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.celery import app


def moneygram_notify(to_process_ids: list[PaymentRecord]) -> None:
    notify_records_to_fsp(fqn(MoneyGramClient), to_process_ids)


@app.task()  # queue="executors"
def moneygram_send_money(tag=None, threshold=10000):
    """Task to trigger MoneyGram payments."""
    fsp = "MoneyGram"
    fsp_vendor_number = config.MONEYGRAM_VENDOR_NUMBER
    threshold = threshold or config.MONEYGRAM_THREASHOLD
    action_fqn = moneygram_notify
    group_key = "mg-send-instruction"

    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key, threshold, tag)


@app.task
def moneygram_update(ids=None) -> None:
    client = MoneyGramClient()
    qs = PaymentRecord.objects.select_related("parent__fsp").filter(
        parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
        parent__status=PaymentInstructionState.PROCESSED,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    if ids:
        qs = qs.filter(id__in=ids)
    for record in qs:
        client.status_update(record.get_payload())
