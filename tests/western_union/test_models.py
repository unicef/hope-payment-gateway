import pytest

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
def test_payment_record_log():
    prl = PaymentRecordFactory(record_code="RCD-123", message="OK")
    assert str(prl) == "RCD-123 / OK"


@pytest.mark.django_db
def test_payment_record_log_payload():
    instruction = PaymentInstructionFactory(payload={"a": "a"})
    prl = PaymentRecordFactory(parent=instruction, payload={"b": "b"}, record_code="r")
    assert prl.get_payload().keys() == {"a", "b", "payment_record_code", "record_uuid"}
