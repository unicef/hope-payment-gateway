import pytest
from viewflow.fsm.base import TransitionNotAllowed

from factories import PaymentInstructionFactory, PaymentRecordFactory
from hope_payment_gateway.apps.gateway.flows import PaymentInstructionFlow, PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    PaymentInstructionState,
    PaymentRecordState,
)


@pytest.fixture
def make_instruction():
    def _make(status):
        return PaymentInstructionFactory(status=status)

    return _make


@pytest.fixture
def make_record():
    def _make(status):
        return PaymentRecordFactory(status=status)

    return _make


@pytest.mark.django_db
class TestPaymentInstructionFlow:
    @pytest.mark.parametrize(
        ("transition", "source", "target"),
        [
            ("open", PaymentInstructionState.DRAFT, PaymentInstructionState.OPEN),
            ("close", PaymentInstructionState.OPEN, PaymentInstructionState.CLOSED),
            ("ready", PaymentInstructionState.CLOSED, PaymentInstructionState.READY),
            ("process", PaymentInstructionState.READY, PaymentInstructionState.PROCESSED),
            ("finalize", PaymentInstructionState.OPEN, PaymentInstructionState.FINALIZED),
            ("finalize", PaymentInstructionState.CLOSED, PaymentInstructionState.FINALIZED),
            ("finalize", PaymentInstructionState.READY, PaymentInstructionState.FINALIZED),
            ("finalize", PaymentInstructionState.PROCESSED, PaymentInstructionState.FINALIZED),
            ("abort", PaymentInstructionState.DRAFT, PaymentInstructionState.ABORTED),
            ("abort", PaymentInstructionState.OPEN, PaymentInstructionState.ABORTED),
            ("abort", PaymentInstructionState.CLOSED, PaymentInstructionState.ABORTED),
            ("abort", PaymentInstructionState.READY, PaymentInstructionState.ABORTED),
            ("abort", PaymentInstructionState.PROCESSED, PaymentInstructionState.ABORTED),
            ("abort", PaymentInstructionState.FINALIZED, PaymentInstructionState.ABORTED),
        ],
    )
    def test_transitions_ok(self, transition, source, target, make_instruction):
        instruction = make_instruction(status=source)
        flow = PaymentInstructionFlow(instruction)
        getattr(flow, transition)()
        assert instruction.status == target

    @pytest.mark.parametrize(
        ("transition", "source"),
        [
            ("open", PaymentInstructionState.OPEN),
            ("open", PaymentInstructionState.CLOSED),
            ("close", PaymentInstructionState.DRAFT),
            ("close", PaymentInstructionState.READY),
            ("ready", PaymentInstructionState.OPEN),
            ("ready", PaymentInstructionState.PROCESSED),
            ("process", PaymentInstructionState.CLOSED),
            ("process", PaymentInstructionState.FINALIZED),
            ("finalize", PaymentInstructionState.DRAFT),
            ("finalize", PaymentInstructionState.ABORTED),
        ],
    )
    def test_transitions_ko(self, transition, source, make_instruction):
        instruction = make_instruction(status=source)
        flow = PaymentInstructionFlow(instruction)
        with pytest.raises((TransitionNotAllowed, AssertionError)):
            getattr(flow, transition)()
        assert instruction.status == source


@pytest.mark.django_db
class TestPaymentRecordFlow:
    @pytest.mark.parametrize(
        ("transition", "source", "target"),
        [
            ("store", PaymentRecordState.PENDING, PaymentRecordState.TRANSFERRED_TO_FSP),
            ("confirm", PaymentRecordState.TRANSFERRED_TO_FSP, PaymentRecordState.TRANSFERRED_TO_BENEFICIARY),
            ("purge", PaymentRecordState.TRANSFERRED_TO_FSP, PaymentRecordState.PURGED),
            ("refund", PaymentRecordState.TRANSFERRED_TO_FSP, PaymentRecordState.REFUND),
            ("cancel", PaymentRecordState.PENDING, PaymentRecordState.CANCELLED),
            ("cancel", PaymentRecordState.TRANSFERRED_TO_FSP, PaymentRecordState.CANCELLED),
            ("fail", PaymentRecordState.PENDING, PaymentRecordState.ERROR),
            ("fail", PaymentRecordState.TRANSFERRED_TO_FSP, PaymentRecordState.ERROR),
            ("fail", PaymentRecordState.TRANSFERRED_TO_BENEFICIARY, PaymentRecordState.ERROR),
            ("unpay", PaymentRecordState.TRANSFERRED_TO_BENEFICIARY, PaymentRecordState.TRANSFERRED_TO_FSP),
        ],
    )
    def test_transitions_ok(self, transition, source, target, make_record):
        record = make_record(status=source)
        flow = PaymentRecordFlow(record)
        getattr(flow, transition)()
        assert record.status == target

    @pytest.mark.parametrize(
        ("transition", "source"),
        [
            ("store", PaymentRecordState.TRANSFERRED_TO_FSP),
            ("confirm", PaymentRecordState.PENDING),
            ("confirm", PaymentRecordState.PURGED),
            ("purge", PaymentRecordState.PENDING),
            ("refund", PaymentRecordState.PENDING),
            ("unpay", PaymentRecordState.PENDING),
            ("unpay", PaymentRecordState.TRANSFERRED_TO_FSP),
        ],
    )
    def test_transitions_ko(self, transition, source, make_record):
        record = make_record(status=source)
        flow = PaymentRecordFlow(record)
        with pytest.raises((TransitionNotAllowed, AssertionError)):
            getattr(flow, transition)()
        assert record.status == source
