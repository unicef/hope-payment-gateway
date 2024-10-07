from unittest.mock import MagicMock, call

from pytest_mock import MockerFixture

from hope_payment_gateway.apps.fsp.moneygram.tasks import moneygram_notify


def test_transactions_are_created_for_ids(mocker: MockerFixture) -> None:
    payment_record = MagicMock()
    payment_record_model = mocker.patch("hope_payment_gateway.apps.fsp.moneygram.tasks.PaymentRecord")
    payment_record_model.objects.filter.return_value.__iter__.return_value = iter((payment_record,))
    money_gram_client = mocker.patch("hope_payment_gateway.apps.fsp.moneygram.tasks.MoneyGramClient")
    ids = MagicMock()

    moneygram_notify(ids)

    payment_record_model.objects.filter.assert_has_calls((call(id_in=ids).update(marked_for_payment=True),))
    money_gram_client.return_value.create_transaction.assert_called_once_with(payment_record.get_payload.return_value)
