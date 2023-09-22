from unittest.mock import patch

import pytest
from constance.test import override_config

from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord
from hope_payment_gateway.apps.western_union.tasks import send_money_task

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
@override_config(WESTERN_UNION_THREASHOLD=10)
@patch("hope_payment_gateway.apps.western_union.tasks.send_money")
def test_send_money_task(mock_class, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(status=PaymentInstruction.READY)
    instr_b = PaymentInstructionFactory(status=PaymentInstruction.READY)
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecord.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecord.PENDING)

    instr_noise = PaymentInstructionFactory(status=PaymentInstruction.OPEN)
    PaymentRecordFactory.create_batch(5, parent=instr_a, status=PaymentRecord.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecord.PENDING)

    send_money_task()
    assert len(mock_class.mock_calls) == total
