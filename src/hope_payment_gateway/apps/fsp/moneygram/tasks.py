import logging
from typing import List

from constance import config

from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.celery import app


@app.task()  # queue="executors"
def moneygram_send_task(vendor_number="1900723202", tag=None, threshold=10000):
    """Task to trigger MoneyGram payments"""
    logging.info("MoneyGram Task started")
    fsp = FinancialServiceProvider.objects.get(vision_vendor_number=vendor_number)
    threshold = threshold or config.MONEYGRAM_THREASHOLD

    records_count = 0

    qs = PaymentInstruction.objects.filter(status=PaymentInstructionState.READY, fsp=fsp)
    if tag:
        qs = qs.filter(tag=tag)

    for pi in qs:
        logging.info(f"Processing payment instruction {pi.unicef_id}")
        records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING, marked_for_payment=False)
        records_count += records.count()
        if records_count > threshold:
            break

        logging.info(f"Sending {records_count} records {pi} to Moneygram")
        records_ids = list(records.values_list("id", flat=True))
        moneygram_notify.delay(records_ids)
        pi.status = PaymentInstructionState.PROCESSED
        pi.save()

    logging.info("MoneyGram Task completed")


@app.task
def moneygram_notify(to_process_ids: List[PaymentRecord]) -> None:
    PaymentRecord.objects.filter(id__in=to_process_ids).update(marked_for_payment=True)
    for record in PaymentRecord.objects.filter(id__in=to_process_ids):
        MoneyGramClient().create_transaction(record.get_payload())
