import pytest
from django_fsm import TransitionNotAllowed

from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord

from ..factories import CorridorFactory, PaymentInstructionFactory, PaymentRecordFactory


@pytest.mark.django_db
def test_corridor():
    corridor = CorridorFactory(description="Corridor", template_code="TMP")
    assert str(corridor) == "Corridor / TMP"


@pytest.mark.django_db
def test_payment_instruction():
    instruction = PaymentInstructionFactory(unicef_id="UNC-123")
    assert str(instruction) == "UNC-123 - DRAFT"


@pytest.mark.django_db
def test_payment_record():
    prl = PaymentRecordFactory(record_code="RCD-123", message="OK")
    assert str(prl) == "RCD-123 / OK"


@pytest.mark.django_db
def test_payment_record_payload():
    instruction = PaymentInstructionFactory(payload={"a": "a"})
    prl = PaymentRecordFactory(parent=instruction, payload={"b": "b"}, record_code="r")
    assert prl.get_payload().keys() == {"a", "b", "payment_record_code", "record_uuid"}


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("open", "DRAFT", "OPEN"),
        ("ready", "OPEN", "READY"),
        ("close", "READY", "CLOSED"),
        ("cancel", "DRAFT", "CANCELLED"),
        ("cancel", "READY", "CANCELLED"),
    ],
)
@pytest.mark.django_db
def test_payment_instruction_transactions_ok(transaction_name, source, destination):
    instruction = PaymentInstructionFactory(status=getattr(PaymentInstruction, source))
    transaction = getattr(instruction, transaction_name)
    transaction()
    assert instruction.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("open", "DRAFT", "CANCELLED"),
        ("ready", "OPEN", "DRAFT"),
        ("close", "DRAFT", "CLOSED"),
        ("cancel", "DRAFT", "CLOSED"),
    ],
)
@pytest.mark.django_db
def test_payment_instruction_transactions_ko(transaction_name, source, destination):
    instruction = PaymentInstructionFactory(status=getattr(PaymentInstruction, source))
    transaction = getattr(instruction, transaction_name)
    with pytest.raises((TransitionNotAllowed, AssertionError)):
        transaction()
        assert instruction.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("validate", "PENDING", "VALIDATION_OK"),
        ("store", "VALIDATION_OK", "TRANSFERRED_TO_FSP"),
        ("confirm", "TRANSFERRED_TO_FSP", "TRANSFERRED_TO_BENEFICIARY"),
        ("cancel", "TRANSFERRED_TO_FSP", "CANCELLED"),
        ("fail", "VALIDATION_OK", "ERROR"),
        ("fail", "TRANSFERRED_TO_BENEFICIARY", "ERROR"),
    ],
)
@pytest.mark.django_db
def test_payment_record_transactions_ok(transaction_name, source, destination):
    record = PaymentRecordFactory(status=getattr(PaymentRecord, source))
    transaction = getattr(record, transaction_name)
    transaction()
    assert record.status == destination


@pytest.mark.parametrize(
    "transaction_name,source,destination",
    [
        ("validate", "PENDING", "TRANSFERRED_TO_FSP"),
        ("store", "VALIDATION_OK", "PENDING"),
        ("confirm", "PENDING", "TRANSFERRED_TO_BENEFICIARY"),
        ("cancel", "PENDING", "ERROR"),
        ("fail", "VALIDATION_OK", "CANCELLED"),
        ("cancel", "TRANSFERRED_TO_BENEFICIARY", "ERROR"),
        ("fail", "TRANSFERRED_TO_BENEFICIARY", "CANCELLED"),
    ],
)
@pytest.mark.django_db
def test_payment_record_transactions_ko(transaction_name, source, destination):
    instruction = PaymentRecordFactory(status=getattr(PaymentRecord, source))
    transaction = getattr(instruction, transaction_name)
    with pytest.raises((TransitionNotAllowed, AssertionError)):
        transaction()
        assert instruction.status == destination
