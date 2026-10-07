from datetime import date
from unittest.mock import Mock, patch
import pytest
import responses
from constance.test import override_config
from factories import PaymentRecordFactory
from zeep.exceptions import TransportError

from hope_payment_gateway.api.western_union.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


# @_recorder.record(file_path="tests/western_union/endpoints/status.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status(wu, wu_client, payment_record_status):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/status.yaml")
    pr = payment_record_status
    resp = wu_client.status(pr.fsp_code, True)
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
    assert pr.payout_amount == 1000.00
    assert pr.payout_date == date(2024, 12, 18)
    assert (resp["title"], resp["code"]) == ("PayStatus", 200)


@pytest.fixture
def payment_record_status(wu):
    ref_no = "Y3snz233UkGt1Gw4"
    mtcn = "8560724095"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
    }
    return PaymentRecordFactory.create(
        fsp_code=mtcn,
        record_code=ref_no,
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
            "channel": {"type": "H2H", "name": "TEST", "version": "9500"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_paid_without_payout_fields(wu, wu_client, payment_record_status_paid_without_payout):
    pr = payment_record_status_paid_without_payout
    mock_response = {
        "content_response": {"payment_transactions": {"payment_transaction": [{"pay_status_description": "PAID"}]}}
    }
    with patch.object(wu_client, "response_context", return_value=mock_response):
        resp = WesternUnionClient().status(pr.fsp_code, True)
        pr.refresh_from_db()
        assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
        assert pr.message == "Transferred to Beneficiary*"
        assert pr.payout_amount is None
        assert pr.payout_date is None
        assert resp == mock_response


@pytest.fixture
def payment_record_status_paid_without_payout(wu):
    ref_no = "Y3snz233UkGt1Gw4"
    mtcn = "8560724095"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
    }
    return PaymentRecordFactory.create(
        fsp_code=mtcn,
        record_code=ref_no,
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
            "channel": {"type": "H2H", "name": "TEST", "version": "9500"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )


@pytest.mark.parametrize(
    ("pr_status", "response_status", "message"),
    [
        (PaymentRecordState.TRANSFERRED_TO_FSP, "WCQ", "Transferred to FSP*"),
        (PaymentRecordState.CANCELLED, "CAN", "Cancelled*"),
    ],
)
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_no_matching_status(
    wu, wu_client, payment_record_status_no_matching, pr_status, response_status, message
):
    pr = payment_record_status_no_matching
    mock_response = {
        "content_response": {
            "payment_transactions": {"payment_transaction": [{"pay_status_description": response_status}]}
        }
    }
    with patch.object(wu_client, "response_context", return_value=mock_response):
        resp = WesternUnionClient().status(pr.fsp_code, True)
        pr.refresh_from_db()
        assert pr.message == message
        assert pr.status == pr_status
        assert pr.success is True
        assert resp == mock_response


@pytest.fixture
def payment_record_status_no_matching(wu):
    ref_no = "Y3snz233UkGt1Gw4"
    mtcn = "8560724095"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
    }
    return PaymentRecordFactory.create(
        fsp_code=mtcn,
        record_code=ref_no,
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
            "channel": {"type": "H2H", "name": "TEST", "version": "9500"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_BENEFICIARY,
    )


@pytest.mark.parametrize(
    "mock_response,missing_key",
    [
        ({}, "'content_response'"),
        ({"content_response": {}}, "'payment_transactions'"),
        (
            {"content_response": {"payment_transactions": {}}},
            "'payment_transaction'",
        ),
        (
            {"content_response": {"payment_transactions": {"payment_transaction": [{}]}}},
            "'pay_status_description'",
        ),
    ],
    ids=[
        "missing_content_response",
        "missing_payment_transactions",
        "missing_payment_transaction",
        "missing_pay_status_description",
    ],
)
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_update_key_error(wu, wu_client, payment_record_status_no_matching, mock_response, missing_key):
    pr = payment_record_status_no_matching
    with patch.object(wu_client, "response_context", return_value=mock_response):
        resp = WesternUnionClient().status(pr.fsp_code, True)
        pr.refresh_from_db()
        assert resp["code"] == 400
        assert missing_key in resp["title"]
        assert resp["error"] == mock_response
        assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_update_type_error(wu, wu_client, payment_record_status_no_matching):
    pr = payment_record_status_no_matching
    mock_response = {
        "content_response": {
            "payment_transactions": {"payment_transaction": ["Transaction not found"]},
        }
    }
    with patch.object(wu_client, "response_context", return_value=mock_response):
        resp = WesternUnionClient().status(pr.fsp_code, True)
        pr.refresh_from_db()
        assert resp["code"] == 400
        assert resp["error"] == mock_response
        assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_update_upstream_failure(wu, wu_client, payment_record_status_no_matching):
    pr = payment_record_status_no_matching
    service = Mock()
    service.PayStatus.side_effect = TransportError("Transport Error", status_code=500)
    with patch.object(wu_client.status_client, "bind", return_value=service):
        resp = WesternUnionClient().status(pr.fsp_code, True)
        pr.refresh_from_db()
        assert resp["code"] == 400
        assert resp["title"] == "Transport Error [500]"
        assert resp["content_response"] is None
        assert "Missing key" not in resp["title"]
        assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_uses_auth_code_mtcn(wu, wu_client):
    pr = PaymentRecordFactory.create(
        fsp_code="2323589126420060",
        record_code="ref-1",
        auth_code="0123456789",
        fsp_data={
            "mtcn": 123456789,
            "foreign_remote_system": {"identifier": "IDENTIFIER", "reference_no": "REFNO", "counter_id": "COUNTER"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    mock_response = {
        "content_response": {"payment_transactions": {"payment_transaction": [{"pay_status_description": "PAID"}]}}
    }
    with patch.object(wu_client, "response_context", return_value=mock_response) as mock_ctx:
        WesternUnionClient().status(pr.fsp_code, True)
    sent_payload = mock_ctx.call_args.args[2]
    assert sent_payload["mtcn"] == "0123456789"
    assert len(sent_payload["mtcn"]) == 10


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_update_no_key_error_on_false(wu, wu_client, payment_record_status_no_matching):
    pr = payment_record_status_no_matching
    mock_response = {}
    with patch.object(wu_client, "response_context", return_value=mock_response):
        resp = WesternUnionClient().status(pr.fsp_code, False)
        assert resp == mock_response
