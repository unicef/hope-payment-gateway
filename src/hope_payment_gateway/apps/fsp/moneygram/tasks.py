import logging

from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
    FinancialServiceProviderConfig,
)
from hope_payment_gateway.config.celery import app


def moneygram_notify(to_process_ids: list[PaymentRecord]) -> None:
    client = MoneyGramClient()
    for record in PaymentRecord.objects.select_related("parent__fsp").filter(id__in=to_process_ids):
        client.create_transaction(record.get_payload())


@app.task()  # queue="executors"
def moneygram_send_money(tag=None, threshold=10000):
    """Task to trigger MoneyGram payments."""
    logging.info("MoneyGram Task started")
    threshold = threshold or config.MONEYGRAM_THREASHOLD

    records_count = 0

    qs = PaymentInstruction.objects.filter(
        status=PaymentInstructionState.READY, fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER, active=True
    )
    if tag:
        qs = qs.filter(tag=tag)

    for pi in qs:
        logging.info(f"Processing payment instruction {pi.external_code}")
        records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING)
        records_count += records.count()
        if records_count > threshold:
            break

        logging.info(f"Sending {records_count} records {pi} to MoneyGram")
        records_ids = list(records.values_list("id", flat=True))
        job = AsyncJob.objects.create(
            description="Send Instruction to MoneyGram",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(moneygram_notify),
            config={"to_process_ids": records_ids},
            instruction=pi,
            group_key="mg-send-instruction",
        )
        with lock_job(job):
            job.queue()
            pi.status = PaymentInstructionState.PROCESSED
            pi.save()

    logging.info("MoneyGram Task completed")


@app.task
def moneygram_update(ids=None) -> None:
    qs = PaymentRecord.objects.select_related("parent__fsp").filter(
        parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
        parent__status=PaymentInstructionState.PROCESSED,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    client = MoneyGramClient()
    if ids:
        qs = qs.filter(id__in=ids)
    for record in qs:
        agent_partner_id = FinancialServiceProviderConfig.objects.get(
            fsp=record.parent.fsp,
            delivery_mechanism__code=record.get_payload()["delivery_mechanism"],
            key=record.get_payload()["config_key"],
        ).configuration["agent_partner_id"]
        client.query_status(record.fsp_code, agent_partner_id, True)
