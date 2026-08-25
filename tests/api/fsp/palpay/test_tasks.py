from unittest.mock import patch, MagicMock

import pytest
import requests
from constance.test import override_config
from django.test import override_settings
from factories import PaymentInstructionFactory, PaymentRecordFactory

from hope_payment_gateway.apps.fsp.palpay.tasks import (
    palpay_notify,
    palpay_money_transfer,
    palpay_send_money,
    palpay_send_money_cash,
)
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState


@pytest.fixture
def palpay_instruction(palpay):
    return PaymentInstructionFactory(fsp=palpay)


@pytest.fixture
def palpay_instruction_with_record(palpay):
    instruction = PaymentInstructionFactory(fsp=palpay, external_code="INST-001")
    PaymentRecordFactory(
        parent=instruction,
        payload={
            "first_name": "John",
            "middle_name": "M",
            "last_name": "Doe",
            "mobile": "+970591234567",
            "amount": 100,
        },
    )
    return instruction


@pytest.fixture
def palpay_instruction_with_record_error(palpay):
    instruction = PaymentInstructionFactory(fsp=palpay, external_code="INST-002")
    PaymentRecordFactory(
        parent=instruction,
        payload={
            "first_name": "Jane",
            "middle_name": "",
            "last_name": "Smith",
            "mobile": "+970599876543",
            "amount": 200,
        },
    )
    return instruction


@pytest.fixture
def palpay_cash_instructions(palpay):
    PaymentInstructionFactory(
        fsp=palpay,
        status=PaymentInstructionState.READY,
        active=True,
        external_code="CASH-001",
    )
    PaymentInstructionFactory(
        fsp=palpay,
        status=PaymentInstructionState.READY,
        active=True,
        external_code="CASH-002",
    )


@pytest.fixture
def palpay_tagged_instructions(palpay):
    PaymentInstructionFactory(
        fsp=palpay,
        status=PaymentInstructionState.READY,
        active=True,
        tag="mytag",
        external_code="TAG-001",
    )
    PaymentInstructionFactory(
        fsp=palpay,
        status=PaymentInstructionState.READY,
        active=True,
        tag="othertag",
        external_code="TAG-002",
    )


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.notify_records_to_fsp")
def test_palpay_notify(mock_notify, palpay_instruction):
    palpay_notify(palpay_instruction.pk)
    mock_notify.assert_called_once()


@pytest.mark.django_db
@override_settings(PALPAY_INSTRUCTION_POST="https://palpay.example.com/api/instruction")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.requests.post")
def test_palpay_money_transfer_success(mock_post, palpay_instruction_with_record):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    result = palpay_money_transfer(palpay_instruction_with_record.pk)

    assert result["status"] == "success"
    assert result["code"] == 200
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://palpay.example.com/api/instruction"
    assert "file" in call_kwargs[1]["files"]


@pytest.mark.django_db
@override_settings(PALPAY_INSTRUCTION_POST="https://palpay.example.com/api/instruction")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.requests.post")
def test_palpay_money_transfer_error(mock_post, palpay_instruction_with_record_error):
    mock_post.side_effect = requests.ConnectionError("Connection refused")

    result = palpay_money_transfer(palpay_instruction_with_record_error.pk)

    assert result["status"] == "error"
    assert "Connection refused" in result["message"]


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.send_to_fsp")
def test_palpay_send_money(mock_send_to_fsp, palpay):
    palpay_send_money()
    mock_send_to_fsp.assert_called_once()


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.lock_job")
def test_palpay_send_money_cash_no_instructions(mock_lock, palpay):
    mock_lock.return_value.__enter__ = MagicMock()
    mock_lock.return_value.__exit__ = MagicMock(return_value=False)

    palpay_send_money_cash()

    from hope_payment_gateway.apps.gateway.models import AsyncJob

    assert AsyncJob.objects.count() == 0


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.lock_job")
def test_palpay_send_money_cash_with_instructions(mock_lock, palpay, palpay_cash_instructions):
    mock_lock.return_value.__enter__ = MagicMock()
    mock_lock.return_value.__exit__ = MagicMock(return_value=False)

    from hope_payment_gateway.apps.gateway.models import AsyncJob

    initial_count = AsyncJob.objects.count()
    palpay_send_money_cash()
    assert AsyncJob.objects.count() == initial_count + 2


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.fsp.palpay.tasks.lock_job")
def test_palpay_send_money_cash_with_tag(mock_lock, palpay, palpay_tagged_instructions):
    mock_lock.return_value.__enter__ = MagicMock()
    mock_lock.return_value.__exit__ = MagicMock(return_value=False)

    from hope_payment_gateway.apps.gateway.models import AsyncJob

    initial_count = AsyncJob.objects.count()
    palpay_send_money_cash(tag="mytag")
    assert AsyncJob.objects.count() == initial_count + 1
