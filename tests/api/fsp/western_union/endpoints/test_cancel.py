from unittest.mock import patch
import pytest
import responses
from constance.test import override_config
from factories import PaymentRecordFactory
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


# @_recorder.record(file_path="tests/api/fsp/western_union/endpoints/search_request.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_search_request(wu, wu_client, payment_record_search_request):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/search_request.yaml")
    _, mtcn, frm = (
        "Y3snz233UkGt1Gw4",
        "0352466394",
        {
            "identifier": "IDENTIFIER",
            "reference_no": "REFNO",
            "counter_id": "COUNTER",
            "operator_id": None,
            "partnership_indicator": None,
        },
    )

    resp = wu_client.search_request(frm, mtcn)
    assert (resp["title"], resp["code"]) == ("Search", 200)


@pytest.fixture
def payment_record_search_request(wu):
    ref_no = "Y3snz233UkGt1Gw4"
    mtcn = "0352466394"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
        "operator_id": None,
        "partnership_indicator": None,
    }
    return PaymentRecordFactory.create(
        record_code=ref_no,
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
        parent__fsp=wu,
    )


# @_recorder.record(file_path="tests/api/fsp/western_union/endpoints/cancel_complete.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_cancel(wu, wu_client, payment_record_for_cancel):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/cancel.yaml")
    pl = payment_record_for_cancel
    wu_client.refund(pl.fsp_code, pl.payload)
    pl.refresh_from_db()
    assert pl.message, pl.success == ("Cancelled", True)


@pytest.fixture
def payment_record_for_cancel(wu):
    mtcn = "0352466394"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
        "operator_id": None,
        "partnership_indicator": None,
    }
    return PaymentRecordFactory.create(
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
        parent__fsp=wu,
    )


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_search_ko(wu, wu_client, payment_record_search_ko):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/search_ko.yaml")
    pl = payment_record_search_ko
    wu_client.refund(pl.fsp_code, pl.payload)
    pl.refresh_from_db()
    assert pl.message == "Search Error: No Money Transfer Key"
    assert not pl.success
    assert pl.status == PaymentRecordState.ERROR


@pytest.fixture
def payment_record_search_ko(wu):
    return PaymentRecordFactory.create(parent__fsp=wu)


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_cancel_type_error(wu, wu_client, payment_record_cancel_type_error):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/cancel.yaml")

    search_request_mock_response = {"content_response": None}
    with patch.object(wu_client, "search_request", return_value=search_request_mock_response):
        pl = payment_record_cancel_type_error
        wu_client.refund(pl.fsp_code, pl.payload)
        pl.refresh_from_db()
        assert pl.message, pl.success == ("Cancelled", True)


@pytest.fixture
def payment_record_cancel_type_error(wu):
    mtcn = "0352466394"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
        "operator_id": None,
        "partnership_indicator": None,
    }
    return PaymentRecordFactory.create(
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
        parent__fsp=wu,
    )


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_cancel_request_not_successful(wu, wu_client, payment_record_cancel_request_not_successful):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/cancel.yaml")

    search_request_mock_response = {"code": 400, "error": "Error"}
    with patch.object(wu_client, "cancel_request", return_value=search_request_mock_response):
        pl = payment_record_cancel_request_not_successful
        wu_client.refund(pl.fsp_code, pl.payload)
        pl.refresh_from_db()
        assert pl.message, pl.success == (f"Cancel request error: {search_request_mock_response['error']}", False)


@pytest.fixture
def payment_record_cancel_request_not_successful(wu):
    mtcn = "0352466394"
    frm = {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
        "operator_id": None,
        "partnership_indicator": None,
    }
    return PaymentRecordFactory.create(
        fsp_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
        parent__fsp=wu,
    )
