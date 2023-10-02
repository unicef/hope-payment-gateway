from unittest.mock import patch

import pytest

from hope_payment_gateway.apps.fsp.western_union.tasks import western_union_send_task
from hope_payment_gateway.apps.gateway.models import PaymentInstruction, PaymentRecord

from ..factories import PaymentInstructionFactory, PaymentRecordFactory


@pytest.mark.parametrize(
    "rec_a,rec_b,total",
    [
        (5, 4, 9),
        (5, 8, 10),
        (20, 0, 10),
        (4, 0, 4),
        (0, 4, 4),
        (0, 0, 0),
    ],
)
@pytest.mark.django_db
@patch("hope_payment_gateway.apps.fsp.western_union.handlers.send_money")
def test_send_money_task(mock_class, wu, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(status=PaymentInstruction.READY, fsp=wu, tag="tag")
    instr_b = PaymentInstructionFactory(status=PaymentInstruction.READY, fsp=wu, tag="tag")
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecord.PENDING)

    instr_noise = PaymentInstructionFactory(status=PaymentInstruction.OPEN)
    instr_noise_no_tag = PaymentInstructionFactory(status=PaymentInstruction.OPEN)
    PaymentRecordFactory.create_batch(5, parent=instr_a, status=PaymentRecord.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(5, parent=instr_noise_no_tag, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(5, parent__status=PaymentRecord.PENDING, status=PaymentRecord.PENDING)

    western_union_send_task(vision_vendor_number="1900723202", tag="tag", threshold=10)
    assert len(mock_class.mock_calls) == total
