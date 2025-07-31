import logging
from io import BytesIO

import openpyxl
import requests
from constance import config
from django.conf import settings
from strategy_field.utils import fqn

from hope_payment_gateway.apps.core.tasks import lock_job
from hope_payment_gateway.apps.fsp.palpay.client import PalPayClient
from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp, send_to_fsp
from hope_payment_gateway.apps.gateway.models import (
    PaymentRecord, PaymentInstruction, PaymentInstructionState, PaymentRecordState, AsyncJob,
)
from hope_payment_gateway.config.celery import app


def palpay_notify(to_process_ids: list[PaymentRecord]) -> None:
    notify_records_to_fsp(fqn(PalPayClient), to_process_ids)


# for user in User.objects.all():
#     print(user.username, user.last_login, user.status, )
def palpay_money_transfer(pk: int) -> None:
    instruction = PaymentInstruction.objects.get(pk=pk)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = instruction.external_code

    ws.append(["ID", "Full Name", "Mobile", "Amount"])

    for record in PaymentRecord.objects.filter(parent=instruction):
        payload = record.payload
        ws.append([
            record.id,
            " ".join(payload[value] for value in ["first_name", "middle_name", "last_name"] if payload.get(value)),
            payload["mobile"],
            payload["mobile"],
        ])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    files = {'file': (f'{ws.title}.xlsx', file_stream, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    try:
        response = requests.post(settings.PALPAY_INSTRUCTION_POST, files=files)
        response.raise_for_status()
        return {"status": "success", "code": response.status_code}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


@app.task()  # queue="executors"
def palpay_send_money(tag=None, threshold=10000):
    """Task to trigger PalPay payments."""
    fsp = "PalPay"
    fsp_vendor_number = config.PALPAY_VENDOR_NUMBER
    threshold = threshold or config.PALPAY_THREASHOLD
    action_fqn = palpay_notify
    group_key = "pal-send-instruction"

    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key, threshold, tag)



@app.task()  # queue="executors"
def palpay_send_money_cash(tag=None, threshold=10000):
    fsp = "PalPay"
    fsp_vendor_number = config.PALPAY_VENDOR_NUMBER
    action_fqn = palpay_notify
    group_key = "pal-send-money-instruction"
    logging.info(f"{fsp} Money Task started")
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
        job = AsyncJob.objects.create(
            description=f"Send Instruction to {fsp}",
            type=AsyncJob.JobType.STANDARD_TASK,
            action=fqn(action_fqn),
            config={"to_process_ids": pi.pk},
            instruction=pi,
            group_key=group_key,
        )
        with lock_job(job):
            job.queue()

    logging.info(f"{fsp} Task completed")
