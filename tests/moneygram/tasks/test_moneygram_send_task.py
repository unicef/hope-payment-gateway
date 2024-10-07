from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from hope_payment_gateway.apps.fsp.moneygram.tasks import moneygram_send_task


def test_moneygram_notify_is_called(mocker: MockerFixture) -> None:
    payment_instruction = MagicMock()

    payment_record = MagicMock()
    payment_records = (payment_record,)
    payment_record_ids = (payment_record.id,)

    payment_instruction.paymentrecord_set.filter.return_value.count.return_value = len(payment_records)
    payment_instruction.paymentrecord_set.filter.return_value.values_list.return_value = payment_record_ids

    payment_instruction_model = mocker.patch("hope_payment_gateway.apps.fsp.moneygram.tasks.PaymentInstruction")
    payment_instruction_model.objects.filter.return_value.__iter__.return_value = iter((payment_instruction,))

    _ = mocker.patch("hope_payment_gateway.apps.fsp.moneygram.tasks.FinancialServiceProvider")

    moneygram_notify = mocker.patch("hope_payment_gateway.apps.fsp.moneygram.tasks.moneygram_notify")

    moneygram_send_task()

    moneygram_notify.delay.assert_called_once_with(list(payment_record_ids))
