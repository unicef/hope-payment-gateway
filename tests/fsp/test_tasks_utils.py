import pytest
from unittest.mock import patch

from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp
from tests.factories import PaymentRecordFactory


@pytest.fixture
def mock_client():
    with patch("hope_payment_gateway.apps.fsp.tasks_utils.import_string") as mock_import:
        mock_client = mock_import.return_value
        yield mock_client


@pytest.mark.django_db
def test_notify_records_to_fsp_success(mock_client):
    record1 = PaymentRecordFactory()
    record2 = PaymentRecordFactory()

    notify_records_to_fsp("client_path", [record1.id, record2.id])

    assert mock_client.create_transaction.call_count == 2


@pytest.mark.django_db
def test_notify_records_to_fsp_with_invalid_ids(mock_client):
    notify_records_to_fsp("client_path", [999, 1000])

    assert mock_client.create_transaction.call_count == 0
