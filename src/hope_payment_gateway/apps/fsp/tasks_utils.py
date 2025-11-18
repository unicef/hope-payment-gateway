import logging

from django.utils.module_loading import import_string
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.exceptions import (
    TokenError,
    PayloadError,
    InvalidCorridorError,
)
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)


def notify_records_to_fsp(client_fqn, instruction_id):
    client = import_string(client_fqn)()
    pi = PaymentInstruction.objects.get(id=instruction_id)
    for record in PaymentRecord.objects.filter(parent=pi, status=PaymentRecordState.PENDING):
        try:
            client.create_transaction(record.get_payload())
        except (TokenError, PayloadError, InvalidCorridorError):
            logging.info(f"{record.record_code} transaction did not success")
    pi.status = PaymentInstructionState.PROCESSED
    pi.save()


def send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key):
    logging.info(f"{fsp} Task started")
    records_count = 0

    qs = PaymentInstruction.objects.select_related("fsp").filter(
        status=PaymentInstructionState.READY,
        fsp__vendor_number=fsp_vendor_number,
        active=True,
    )
    for pi in qs:
        logging.info(f"Processing payment instruction {pi.external_code}")

        logging.info(f"Sending {records_count} records {pi} to {fsp}")
        job = AsyncJob.objects.create(
            description=f"Send Instruction to {fsp}",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(action_fqn),
            config={"instruction_id": pi.id},
            instruction=pi,
            group_key=group_key,
        )
        with lock_job(job):
            job.queue()

    logging.info(f"{fsp} Task completed")
