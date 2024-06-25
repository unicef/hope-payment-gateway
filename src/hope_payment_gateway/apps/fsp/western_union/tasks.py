import logging

from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.das import (
    das_countries_currencies,
    das_delivery_option_template,
)
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.celery import app


@app.task
def western_union_send_task(vision_vendor_number="1900723202", tag=None, threshold=10000):
    fsps = FinancialServiceProvider.objects.filter(vision_vendor_number=vision_vendor_number)
    threshold = threshold or config.DEFAULT_THREASHOLD

    records_count = 0

    for fsp in fsps:
        qs = PaymentInstruction.objects.filter(status=PaymentInstructionState.READY, fsp=fsp)
        if tag:
            qs = qs.filter(tag=tag)

        for pi in qs:
            records = pi.paymentrecord_set.filter(status=PaymentRecordState.PENDING, marked_for_payment=False)
            records_count += records.count()
            if records_count > threshold:
                break

            logging.info(f"Sending {records_count} records {pi} to Western Union")
            fsp.strategy.notify(records)
            pi.status = PaymentInstructionState.PROCESSED
            pi.save()


@app.task
def update_corridors():
    das_countries_currencies(create_corridors=True)


@app.task
def update_templates():
    for corridor in Corridor.objects.all():
        das_delivery_option_template(
            corridor.destination_country, corridor.destination_currency, corridor.template_code
        )
