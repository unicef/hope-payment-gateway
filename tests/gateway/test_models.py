import pytest
from factories import FinancialServiceProviderFactory, PaymentInstructionFactory, PaymentRecordFactory
from viewflow.fsm.base import TransitionNotAllowed

from hope_payment_gateway.apps.gateway.flows import PaymentInstructionFlow, PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)


@pytest.mark.django_db
def test_fsp():
    fsp = FinancialServiceProviderFactory(name="Western Union", vendor_number="007")
    assert str(fsp) == "Western Union [007]"


@pytest.mark.django_db
def test_payment_instruction():
    instruction = PaymentInstructionFactory(unicef_id="UNC-123")
    assert str(instruction) == "UNC-123 - DRAFT"


@pytest.mark.django_db
def test_payment_record():
    prl = PaymentRecordFactory(record_code="RCD-123", message="OK")
    assert str(prl) == "RCD-123 / PENDING"


@pytest.mark.django_db
def test_payment_record_payload():
    instruction = PaymentInstructionFactory(payload={"a": "a"})
    prl = PaymentRecordFactory(parent=instruction, payload={"b": "b"}, record_code="r")
    assert prl.get_payload().keys() == {"a", "b", "payment_record_code", "remote_id"}


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("open", "DRAFT", "OPEN"),
        ("close", "OPEN", "CLOSED"),
        ("ready", "CLOSED", "READY"),
        ("process", "READY", "PROCESSED"),
        ("abort", "DRAFT", "ABORTED"),
        ("abort", "READY", "ABORTED"),
    ],
)
@pytest.mark.django_db
def test_payment_instruction_transactions_ok(transaction_name, source, destination):
    instruction = PaymentInstructionFactory(status=source)
    flow = PaymentInstructionFlow(instruction)
    transaction = getattr(flow, transaction_name)
    transaction()
    assert instruction.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("open", "DRAFT", "CANCELLED"),
        ("ready", "OPEN", "DRAFT"),
        ("close", "DRAFT", "CLOSED"),
        ("abort", "DRAFT", "CLOSED"),
    ],
)
@pytest.mark.django_db
def test_payment_instruction_transactions_ko(transaction_name, source, destination):
    instruction = PaymentInstructionFactory(status=getattr(PaymentInstructionState, source))
    flow = PaymentInstructionFlow(instruction)
    transaction = getattr(flow, transaction_name)
    with pytest.raises((TransitionNotAllowed, AssertionError)):
        transaction()
        assert instruction.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("store", "PENDING", "TRANSFERRED_TO_FSP"),
        ("confirm", "TRANSFERRED_TO_FSP", "TRANSFERRED_TO_BENEFICIARY"),
        ("cancel", "TRANSFERRED_TO_FSP", "CANCELLED"),
        ("fail", "TRANSFERRED_TO_FSP", "ERROR"),
        ("fail", "TRANSFERRED_TO_BENEFICIARY", "ERROR"),
    ],
)
@pytest.mark.django_db
def test_payment_record_transactions_ok(transaction_name, source, destination):
    record = PaymentRecordFactory(status=getattr(PaymentRecordState, source))
    flow = PaymentRecordFlow(record)
    transaction = getattr(flow, transaction_name)
    transaction()
    assert record.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("store", "TRANSFERRED_TO_BENEFICIARY", "PENDING"),
        ("confirm", "PENDING", "TRANSFERRED_TO_BENEFICIARY"),
        ("cancel", "PENDING", "ERROR"),
        ("fail", "PENDING", "CANCELLED"),
        ("cancel", "TRANSFERRED_TO_BENEFICIARY", "ERROR"),
        ("fail", "TRANSFERRED_TO_BENEFICIARY", "CANCELLED"),
    ],
)
@pytest.mark.django_db
def test_payment_record_transactions_ko(transaction_name, source, destination):
    instruction = PaymentRecordFactory(status=getattr(PaymentRecordState, source))
    flow = PaymentRecordFlow(instruction)
    transaction = getattr(flow, transaction_name)
    with pytest.raises((TransitionNotAllowed, AssertionError)):
        transaction()
        assert instruction.status == destination
