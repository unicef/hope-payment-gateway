import logging
from typing import List

from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.das import (
    das_countries_currencies,
    das_delivery_option_template,
)
from hope_payment_gateway.apps.fsp.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.celery import app


@app.task()  # queue="executors"
def western_union_send_task(vision_vendor_number="1900723202", tag=None, threshold=10000):
    """Task to trigger Western Union payments"""
    logging.info("Western Union Task started")
    fsp = FinancialServiceProvider.objects.get(vision_vendor_number=vision_vendor_number)
    threshold = threshold or config.WESTERN_UNION_THREASHOLD

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

        logging.info(f"Sending {records_count} records {pi} to Western Union")
        records_ids = list(records.values_list("id", flat=True))
        western_union_notify.delay(records_ids)
        pi.status = PaymentInstructionState.PROCESSED
        pi.save()

    logging.info("Western Union Task completed")


@app.task
def western_union_notify(to_process_ids: List[PaymentRecord]) -> None:
    PaymentRecord.objects.filter(id__in=to_process_ids).update(marked_for_payment=True)
    for record in PaymentRecord.objects.filter(id__in=to_process_ids):
        send_money(record.get_payload())


@app.task
def update_corridors():
    das_countries_currencies(create_corridors=True)


@app.task
def update_templates():
    for corridor in Corridor.objects.all():
        das_delivery_option_template(
            corridor.destination_country, corridor.destination_currency, corridor.template_code
        )
