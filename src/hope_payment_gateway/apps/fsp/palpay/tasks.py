import logging

from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.palpay.client import PalPayClient
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.celery import app


def palpay_notify(to_process_ids: list[PaymentRecord]) -> None:
    client = PalPayClient()
    for record in PaymentRecord.objects.select_related("parent__fsp").filter(id__in=to_process_ids):
        client.create_transaction(record.get_payload())


@app.task()  # queue="executors"
def palpay_send_money(tag=None, threshold=10000):
    """Task to trigger PalPay payments."""
    logging.info("PalPay Task started")
    threshold = threshold or config.PALPAY_THREASHOLD

    records_count = 0

    qs = PaymentInstruction.objects.filter(
        status=PaymentInstructionState.READY,
        fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        active=True,
    )
    if tag:
        qs = qs.filter(tag=tag)

    for pi in qs:
        logging.info(f"Processing payment instruction {pi.external_code}")
        records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING)
        records_count += records.count()
        if records_count > threshold:
            break

        logging.info(f"Sending {records_count} records {pi} to PalPay")
        records_ids = list(records.values_list("id", flat=True))
        job = AsyncJob.objects.create(
            description="Send Instruction to PalPay",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(palpay_notify),
            config={"to_process_ids": records_ids},
            instruction=pi,
            group_key="mg-send-instruction",
        )
        with lock_job(job):
            job.queue()
            pi.status = PaymentInstructionState.PROCESSED
            pi.save()

    logging.info("PalPay Task completed")


@app.task
def palpay_update(ids=None) -> None:
    qs = PaymentRecord.objects.select_related("parent__fsp").filter(
        parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        parent__status=PaymentInstructionState.PROCESSED,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    client = PalPayClient()
    if ids:
        qs = qs.filter(id__in=ids)
    for record in qs:
        agent_partner_id = FinancialServiceProviderConfig.objects.get(
            fsp=record.parent.fsp,
            delivery_mechanism__code=record.get_payload()["delivery_mechanism"],
            key=record.get_payload()["config_key"],
        ).configuration["agent_partner_id"]
        client.status(record.fsp_code, agent_partner_id, True)
