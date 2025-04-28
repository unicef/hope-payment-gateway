from unittest.mock import patch

import pytest
from constance.test import override_config
from django.test import override_settings
from factories import PaymentInstructionFactory, PaymentRecordFactory

from hope_payment_gateway.apps.fsp.moneygram.tasks import moneygram_send_money, moneygram_update
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState, PaymentRecordState


@pytest.mark.parametrize(
    ("rec_a", "rec_b", "total"),
    [
        (5, 4, 2),
        (5, 8, 1),
        (5, 5, 2),
        (4, 0, 2),
        (0, 4, 2),
        (0, 0, 2),
    ],
)
@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@patch("hope_payment_gateway.apps.fsp.tasks_utils.AsyncJob.queue")
def test_send_money_task(mock_class, mg, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(status=PaymentInstructionState.READY, fsp=mg, tag="tag")
    instr_b = PaymentInstructionFactory(status=PaymentInstructionState.READY, fsp=mg, tag="tag")
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecordState.PENDING)

    instr_noise = PaymentInstructionFactory(status=PaymentInstructionState.OPEN)
    instr_noise_no_tag = PaymentInstructionFactory(status=PaymentInstructionState.OPEN)
    PaymentRecordFactory.create_batch(5, parent=instr_a, status=PaymentRecordState.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent=instr_noise_no_tag, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent__status=PaymentRecordState.PENDING, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(
        5,
        parent__status=PaymentRecordState.PENDING,
        status=PaymentRecordState.PENDING,
    )

    moneygram_send_money(tag="tag", threshold=10)
    assert len(mock_class.mock_calls) == total


@pytest.mark.parametrize(
    ("rec_a", "rec_b", "total"),
    [
        (5, 4, 9),
        (5, 8, 13),
    ],
)
@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@patch("hope_payment_gateway.apps.fsp.moneygram.tasks.MoneyGramClient.status_update")
def test_send_moneygram_update(mock_class, mg, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(
        status=PaymentInstructionState.PROCESSED, fsp=mg, extra={"config_key": "mg-key", "delivery_mechanism": "money"}
    )
    instr_b = PaymentInstructionFactory(
        status=PaymentInstructionState.PROCESSED, fsp=mg, extra={"config_key": "mg-key", "delivery_mechanism": "money"}
    )
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecordState.TRANSFERRED_TO_FSP)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecordState.TRANSFERRED_TO_FSP)

    instr_noise = PaymentInstructionFactory(
        status=PaymentInstructionState.OPEN, extra={"config_key": "mg-key", "delivery_mechanism": "money"}
    )
    instr_noise_no_tag = PaymentInstructionFactory(
        status=PaymentInstructionState.OPEN, extra={"config_key": "mg-key", "delivery_mechanism": "voucher"}
    )
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent=instr_noise_no_tag, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(
        5,
        parent__status=PaymentRecordState.PENDING,
        status=PaymentRecordState.PENDING,
    )

    moneygram_update()
    assert len(mock_class.mock_calls) == total
