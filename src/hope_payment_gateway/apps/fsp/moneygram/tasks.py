import logging
from typing import List

from constance import config

from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.gateway.models import (
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.celery import app


@app.task()  # queue="executors"
def moneygram_send_money(tag=None, threshold=10000):
    """Task to trigger MoneyGram payments"""
    logging.info("MoneyGram Task started")
    threshold = threshold or config.MONEYGRAM_THREASHOLD

    records_count = 0

    qs = PaymentInstruction.objects.filter(
        status=PaymentInstructionState.READY, fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER
    )
    if tag:
        qs = qs.filter(tag=tag)

    for pi in qs:
        logging.info(f"Processing payment instruction {pi.external_code}")
        records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING, marked_for_payment=False)
        records_count += records.count()
        if records_count > threshold:
            break

        logging.info(f"Sending {records_count} records {pi} to MoneyGram")
        records_ids = list(records.values_list("id", flat=True))
        moneygram_notify.delay(records_ids)
        pi.status = PaymentInstructionState.PROCESSED
        pi.save()

    logging.info("MoneyGram Task completed")


@app.task
def moneygram_notify(to_process_ids: List[PaymentRecord]) -> None:
    client = MoneyGramClient()
    PaymentRecord.objects.filter(id__in=to_process_ids).update(
        marked_for_payment=True,
    )
    for record in PaymentRecord.objects.select_related("parent__fsp").filter(id__in=to_process_ids):
        client.create_transaction(record.get_payload())


@app.task
def moneygram_update() -> None:
    client = MoneyGramClient()
    for record in PaymentRecord.objects.select_related("parent__fsp").filter(
        parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
        parent__status=PaymentInstructionState.PROCESSED,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    ):
        client.query_status(record.fsp_code, True)
