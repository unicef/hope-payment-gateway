import responses

from hope_payment_gateway.apps.fsp.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.gateway.models import PaymentRecord

from ...factories import PaymentRecordFactory


# @_recorder.record(file_path="tests/western_union/endpoints/search_request.yaml")
@responses.activate
def test_search_request(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/search_request.yaml")
    ref_no, mtcn, frm = (
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
    PaymentRecordFactory(
        record_code=ref_no,
        extra_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
    )
    resp = search_request(frm, mtcn)
    assert (resp["title"], resp["code"]) == ("Search", 200)


# @_recorder.record(file_path="tests/western_union/endpoints/cancel_complete.yaml")
@responses.activate
def test_cancel(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/endpoints/cancel.yaml")
    mtcn, frm = "0352466394", {
        "identifier": "IDENTIFIER",
        "reference_no": "REFNO",
        "counter_id": "COUNTER",
        "operator_id": None,
        "partnership_indicator": None,
    }
    pl = PaymentRecordFactory(
        extra_data={
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        },
        status=PaymentRecord.TRANSFERRED_TO_FSP,
    )
    cancel(pl.pk)
    pl.refresh_from_db()
    assert pl.message, pl.success == ("Cancelled", True)


@responses.activate
def test_search_ko(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/search_ko.yaml")
    pl = PaymentRecordFactory()
    cancel(pl.pk)
    pl.refresh_from_db()
    assert pl.message == "Search Error: No Money Transfer Key"
    assert not pl.success
    assert pl.status == PaymentRecord.ERROR
