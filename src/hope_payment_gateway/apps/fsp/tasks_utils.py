import logging

from django.utils.module_loading import import_string
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.exceptions import TokenError, PayloadError, InvalidCorridorError
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)


def notify_records_to_fsp(client_fqn, to_process_ids):
    client = import_string(client_fqn)()
    for record in PaymentRecord.objects.filter(id__in=to_process_ids, status=PaymentRecordState.PENDING):
        try:
            client.create_transaction(record.get_payload())
        except (TokenError, PayloadError, InvalidCorridorError):
            logging.info(f"{record.record_code} transaction did not success")


def send_to_fsp(  # noqa
    fsp, fsp_vendor_number, action_fqn, group_key, threshold=None, tag=None
):
    logging.info(f"{fsp} Task started")
    records_count = 0

    qs = PaymentInstruction.objects.select_related("fsp").filter(
        status=PaymentInstructionState.READY,
        fsp__vendor_number=fsp_vendor_number,
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

        logging.info(f"Sending {records_count} records {pi} to {fsp}")
        records_ids = list(records.values_list("id", flat=True))
        job = AsyncJob.objects.create(
            description=f"Send Instruction to {fsp}",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(action_fqn),
            config={"to_process_ids": records_ids},
            instruction=pi,
            group_key=group_key,
        )
        with lock_job(job):
            job.queue()
            pi.status = PaymentInstructionState.PROCESSED
            pi.save()

    logging.info(f"{fsp} Task completed")
