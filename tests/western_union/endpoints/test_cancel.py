import responses

from hope_payment_gateway.apps.western_union.endpoints.cancel import cancel, search_request
from tests.factories import PaymentRecordLogFactory


# @_recorder.record(file_path="tests/western_union/endpoints/search_request.yaml")
@responses.activate
def test_search_request(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/search_request.yaml")
    ref_no, mtcn = "Y3snz233UkGt1Gw4", "0352466394"
    PaymentRecordLogFactory(record_code=ref_no, extra_data={"mtcn": mtcn})
    resp = search_request("Y3snz233UkGt1Gw4", mtcn)
    assert (resp["title"], resp["code"]) == ("Search", 200)


# @_recorder.record(file_path="tests/western_union/endpoints/cancel_complete.yaml")@responses.activate
@responses.activate
def test_cancel(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/endpoints/cancel.yaml")
    ref_no, mtcn = "Y3snz233UkGt1Gw4", "0352466394"
    pl = PaymentRecordLogFactory(record_code=ref_no, extra_data={"mtcn": mtcn})
    cancel(ref_no, mtcn)
    pl.refresh_from_db()
    assert pl.message, pl.success == ("Cancelled", True)


@responses.activate
def test_search_ko(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/search_ko.yaml")
    ref_no, mtcn = "alpha", "6022825782"
    pl = PaymentRecordLogFactory(record_code=ref_no)
    cancel(ref_no, mtcn)
    pl.refresh_from_db()
    assert pl.message, pl.success == ("Cancelled", True)
