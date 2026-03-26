import pytest
from unittest.mock import patch, MagicMock

from factories import PaymentInstructionFactory
from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp
from tests.factories import PaymentRecordFactory


@pytest.fixture
def mock_client():
    with patch("hope_payment_gateway.apps.fsp.tasks_utils.import_string") as mock_import:
        mock_instance = MagicMock()
        mock_class = MagicMock(return_value=mock_instance)
        mock_import.return_value = mock_class
        yield mock_instance


@pytest.mark.django_db
def test_notify_records_to_fsp_success(mock_client):
    pi = PaymentInstructionFactory()
    PaymentRecordFactory.create_batch(2, parent=pi)

    notify_records_to_fsp("client_path", pi.id)

    assert mock_client.create_transaction.call_count == 2


@pytest.mark.django_db
def test_notify_records_to_fsp_with_invalid_ids(mock_client):
    pi = PaymentInstructionFactory()
    notify_records_to_fsp("client_path", pi.id)

    assert mock_client.create_transaction.call_count == 0
