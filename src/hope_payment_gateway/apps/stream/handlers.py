from streaming.utils import make_event
from streaming.manager import initialize_engine


def notify_instruction_change(instruction_pk, status):
    manager = initialize_engine()
    manager.notify(
        "payment.instruction.update",
        make_event(f"Instruction Status Update: {status}", message_id=instruction_pk),
    )


def notify_record_change(record_pk, status):
    manager = initialize_engine()
    manager.notify(
        "payment.record.update",
        make_event(f"Record Status Update: {status}", message_id=record_pk),
    )
