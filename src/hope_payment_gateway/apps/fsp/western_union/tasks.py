import logging

from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    FinancialServiceProvider,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.celery import app


def western_union_notify(to_process_ids: list[PaymentRecord]) -> None:
    for record in PaymentRecord.objects.filter(id__in=to_process_ids):
        WesternUnionClient().create_transaction(record.get_payload())


@app.task()  # queue="executors"
def western_union_send_task(tag=None, threshold=10000):
    """Task to trigger Western Union payments."""
    logging.info("Western Union Task started")
    vendor_number = config.WESTERN_UNION_VENDOR_NUMBER
    threshold = threshold or config.WESTERN_UNION_THREASHOLD
    fsp = FinancialServiceProvider.objects.get(vendor_number=vendor_number)
    records_count = 0
    qs = PaymentInstruction.objects.select_related("fsp").filter(status=PaymentInstructionState.READY, fsp=fsp)
    if tag:
        qs = qs.filter(tag=tag)

    for pi in qs:
        logging.info(f"Processing payment instruction {pi.external_code}")
        records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING)
        records_count += records.count()
        if records_count > threshold:
            break

        logging.info(f"Sending {records_count} records {pi} to Western Union")
        records_ids = list(records.values_list("id", flat=True))
        job = AsyncJob.objects.create(
            description="Send instruction to Western Union",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(western_union_notify),
            config={"to_process_ids": records_ids},
            instruction=pi,
            group_key="wu-send-instruction",
        )
        with lock_job(job):
            job.queue()
            pi.status = PaymentInstructionState.PROCESSED
            pi.save()

    logging.info("Western Union Task completed")


@app.task
def update_corridors():
    WesternUnionClient().das_countries_currencies(create_corridors=True)


@app.task
def update_templates():
    client = WesternUnionClient()
    for corridor in Corridor.objects.all():
        client.das_delivery_option_template(
            corridor.destination_country,
            corridor.destination_currency,
            corridor.template_code,
        )
