from unittest.mock import patch
import pytest
import responses
from constance.test import override_config
from factories import PaymentRecordFactory

from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


# @_recorder.record(file_path="tests/western_union/endpoints/status.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status(wu, wu_client):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/status.yaml")
    ref_no, mtcn, frm = (
        "Y3snz233UkGt1Gw4",
        "8560724095",
        {
            "identifier": "IDENTIFIER",
            "reference_no": "REFNO",
            "counter_id": "COUNTER",
        },
    )
    pr = PaymentRecordFactory(
        fsp_code=mtcn,
        record_code=ref_no,
        extra_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
            "channel": {"type": "H2H", "name": "TEST", "version": "9500"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    resp = wu_client.status(pr.fsp_code, True)
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
    assert (resp["title"], resp["code"]) == ("PayStatus", 200)


@pytest.mark.parametrize(
    ("pr_status", "response_status", "message"),
    [
        (PaymentRecordState.TRANSFERRED_TO_FSP, "WCQ", "Transferred to FSP*"),
        (PaymentRecordState.CANCELLED, "CAN", "Cancelled*"),
    ],
)
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status_no_matching_status(wu, wu_client, pr_status, response_status, message):
    ref_no, mtcn, frm = (
        "Y3snz233UkGt1Gw4",
        "8560724095",
        {
            "identifier": "IDENTIFIER",
            "reference_no": "REFNO",
            "counter_id": "COUNTER",
        },
    )
    pr = PaymentRecordFactory(
        fsp_code=mtcn,
        record_code=ref_no,
        extra_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
            "channel": {"type": "H2H", "name": "TEST", "version": "9500"},
        },
        parent__fsp=wu,
        status=PaymentRecordState.TRANSFERRED_TO_BENEFICIARY,
    )
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
