from unittest.mock import patch

import pytest

from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord
from hope_payment_gateway.apps.western_union.tasks import western_union_send_task

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
@patch("hope_payment_gateway.apps.western_union.handlers.western_union.send_money")
def test_send_money_task(mock_class, wu, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(status=PaymentInstruction.READY, fsp=wu)
    instr_b = PaymentInstructionFactory(status=PaymentInstruction.READY, fsp=wu)
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecord.PENDING)

    instr_noise = PaymentInstructionFactory(status=PaymentInstruction.OPEN)
    PaymentRecordFactory.create_batch(5, parent=instr_a, status=PaymentRecord.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(5, parent__status=PaymentRecord.PENDING, status=PaymentRecord.PENDING)

    western_union_send_task(vision_vendor_number="1900723202", tag=None, threshold=10)
    assert len(mock_class.mock_calls) == total
