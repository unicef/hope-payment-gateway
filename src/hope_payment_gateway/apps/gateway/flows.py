from viewflow import fsm
from viewflow.fsm import State

from hope_payment_gateway.apps.gateway.models import (
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)


class PaymentInstructionFlow:
    state = fsm.State(PaymentInstructionState, default=PaymentInstructionState.DRAFT)

    def __init__(self, obj: PaymentInstruction) -> None:
        self.object = obj

    @state.setter()
    def _set_object_status(self, value: str) -> None:
        self.object.status = value

    @state.getter()
    def _get_object_status(self) -> str:
        return self.object.status

    @state.on_success()
    def _on_transition_success(self, description: str, source: str, target: str) -> None:
        self.object.save()

    @state.transition(
        source=PaymentInstructionState.DRAFT,
        target=PaymentInstructionState.OPEN,
        permission="gateway.change_paymentinstruction",
    )
    def open(self) -> None:
        pass

    @state.transition(
        source=PaymentInstructionState.OPEN,
        target=PaymentInstructionState.CLOSED,
        permission="gateway.change_paymentinstruction",
    )
    def close(self) -> None:
        pass

    @state.transition(
        source=PaymentInstructionState.CLOSED,
        target=PaymentInstructionState.READY,
        permission="gateway.change_paymentinstruction",
    )
    def ready(self) -> None:
        pass

    @state.transition(
        source=PaymentInstructionState.READY,
        target=PaymentInstructionState.PROCESSED,
        permission="gateway.change_paymentinstruction",
    )
    def process(self) -> None:
        pass

    @state.transition(
        source=[
            PaymentInstructionState.OPEN,
            PaymentInstructionState.CLOSED,
            PaymentInstructionState.READY,
            PaymentInstructionState.PROCESSED,
        ],
        target=PaymentInstructionState.FINALIZED,
        permission="gateway.change_paymentinstruction",
    )
    def finalize(self) -> None:
        pass

    @state.transition(
        source=State.ANY,
        target=PaymentInstructionState.ABORTED,
        permission="gateway.change_paymentinstruction",
    )
    def abort(self) -> None:
        pass


class PaymentRecordFlow:
    state = fsm.State(PaymentRecordState, default=PaymentRecordState.PENDING)

    def __init__(self, obj: PaymentRecord) -> None:
        self.object = obj

    @state.setter()
    def _set_object_status(self, value: str) -> None:
        self.object.status = value

    @state.getter()
    def _get_object_status(self) -> str:
        return self.object.status

    @state.on_success()
    def _on_transition_success(self, description: str, source: str, target: str) -> None:
        self.object.save()

    @state.transition(
        source=PaymentRecordState.PENDING,
        target=PaymentRecordState.TRANSFERRED_TO_FSP,
        permission="gateway.change_paymentrecord",
    )
    def store(self) -> None:
        pass

    @state.transition(
        source=PaymentRecordState.TRANSFERRED_TO_FSP,
        target=PaymentRecordState.TRANSFERRED_TO_BENEFICIARY,
        permission="gateway.change_paymentrecord",
    )
    def confirm(self) -> None:
        pass

    @state.transition(
        source=PaymentRecordState.TRANSFERRED_TO_FSP,
        target=PaymentRecordState.PURGED,
        permission="gateway.change_paymentrecord",
    )
    def purge(self) -> None:
        pass

    @state.transition(
        source=PaymentRecordState.TRANSFERRED_TO_FSP,
        target=PaymentRecordState.REFUND,
        permission="gateway.change_paymentrecord",
    )
    def refund(self) -> None:
        pass

    @state.transition(
        source=State.ANY,
        target=PaymentRecordState.CANCELLED,
        permission="gateway.change_paymentrecord",
    )
    def cancel(self) -> None:
        pass

    @state.transition(
        source=State.ANY,
        target=PaymentRecordState.ERROR,
        permission="gateway.change_paymentrecord",
    )
    def fail(self) -> None:
        pass
