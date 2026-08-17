import logging

from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.api.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp, send_to_fsp
from hope_payment_gateway.apps.gateway.models import (
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.celery import app

logger = logging.getLogger(__name__)


def moneygram_notify(instruction_id: int) -> None:
    notify_records_to_fsp(fqn(MoneyGramClient), instruction_id)


@app.task()
def moneygram_send_money():
    """Task to trigger MoneyGram payments."""
    fsp = "MoneyGram"
    fsp_vendor_number = config.MONEYGRAM_VENDOR_NUMBER
    action_fqn = moneygram_notify
    group_key = "mg-send-instruction"

    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key)


@app.task()
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
        try:
            client.status_update(record.get_payload())
        except Exception:
            logger.exception("Failed to update status for record %s", record.record_code)
