import pytest
from unittest.mock import patch, MagicMock

from factories import PaymentInstructionFactory, FinancialServiceProviderFactory
from hope_payment_gateway.apps.fsp.tasks_utils import (
    notify_records_to_fsp,
    send_to_fsp,
)
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    PaymentInstructionState,
)
from hope_payment_gateway.apps.fsp.exceptions import PayloadError, TokenError
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
def test_notify_records_to_fsp_exception(mock_client):
    pi = PaymentInstructionFactory()
    PaymentRecordFactory.create_batch(2, parent=pi)
    mock_client.create_transaction.side_effect = TokenError("Test error")

    notify_records_to_fsp("client_path", pi.id)

    assert mock_client.create_transaction.call_count == 2
    pi.refresh_from_db()
    assert pi.status == PaymentInstructionState.DRAFT


@pytest.mark.django_db
def test_notify_records_to_fsp_partial_success(mock_client):
    pi = PaymentInstructionFactory()
    PaymentRecordFactory.create_batch(3, parent=pi)
    mock_client.create_transaction.side_effect = [
        None,
        PayloadError("fail"),
        None,
    ]

    notify_records_to_fsp("client_path", pi.id)

    assert mock_client.create_transaction.call_count == 3
    pi.refresh_from_db()
    assert pi.status == PaymentInstructionState.PROCESSED


@pytest.mark.django_db
def test_notify_records_to_fsp_with_invalid_ids(mock_client):
    pi = PaymentInstructionFactory()
    notify_records_to_fsp("client_path", pi.id)

    assert mock_client.create_transaction.call_count == 0


@pytest.mark.django_db
def test_send_to_fsp():
    fsp = FinancialServiceProviderFactory(vendor_number="V123")
    pi = PaymentInstructionFactory(fsp=fsp, status=PaymentInstructionState.READY, active=True)
    PaymentInstructionFactory(fsp=fsp, status=PaymentInstructionState.DRAFT, active=True)
    PaymentInstructionFactory(fsp=fsp, status=PaymentInstructionState.READY, active=False)
    fsp2 = FinancialServiceProviderFactory(vendor_number="V456")
    PaymentInstructionFactory(fsp=fsp2, status=PaymentInstructionState.READY, active=True)

    with patch("hope_payment_gateway.apps.fsp.tasks_utils.lock_job") as mock_lock:
        mock_job_instance = MagicMock()
        mock_lock.return_value.__enter__.return_value = mock_job_instance

        send_to_fsp("TestFSP", "V123", "some.action", "group_key")

        # Check if only one AsyncJob was created for the READY and active PI
        assert AsyncJob.objects.count() == 1
        job = AsyncJob.objects.first()
        assert job.instruction == pi
        assert job.group_key == "group_key"
        assert job.config == {"instruction_id": pi.id}
