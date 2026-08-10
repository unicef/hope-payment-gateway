import logging

from django.utils.module_loading import import_string
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.exceptions import (
    InvalidCorridorError,
    PayloadError,
    TokenError,
)
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.signals import payment_instruction_sent_to_fsp


def notify_records_to_fsp(client_fqn: str, instruction_id: int) -> None:
    client = import_string(client_fqn)()
    pi = PaymentInstruction.objects.get(id=instruction_id)
    total = 0
    success_count = 0
    for record in PaymentRecord.objects.filter(parent=pi, status=PaymentRecordState.PENDING):
        total += 1
        try:
            client.create_transaction(record.get_payload())
            success_count += 1
        except TokenError, PayloadError, InvalidCorridorError:
            logging.warning(f"{record.record_code} transaction did not succeed")
    if total > 0 and success_count == total:
        pi.status = PaymentInstructionState.PROCESSED
        pi.save()


def send_to_fsp(fsp: str, fsp_vendor_number: str, action_fqn: str, group_key: str) -> None:
    logging.info(f"{fsp} Task started")

    qs = PaymentInstruction.objects.select_related("fsp").filter(
        status=PaymentInstructionState.READY,
        fsp__vendor_number=fsp_vendor_number,
        active=True,
    )
    for records_count, pi in enumerate(qs, start=1):
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
        payment_instruction_sent_to_fsp.send(sender=PaymentInstruction, instance=pi)

    logging.info(f"{fsp} Task completed")
