import responses

from hope_payment_gateway.apps.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecordLog


# @_recorder.record(file_path="tests/western_union/endpoints/search_request.yaml")
@responses.activate
def test_search_request(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/search_request.yaml")
    ref_no, mtcn = "Y3snz233UkGt1Gw4", "0352466394"
    payment_instruction = PaymentInstruction.objects.create()
    PaymentRecordLog.objects.create(parent=payment_instruction, record_code=ref_no, extra_data={"mtcn": mtcn})
    resp = search_request("Y3snz233UkGt1Gw4", mtcn)
    assert (resp["title"], resp["code"]) == ("Search", 200)


# @_recorder.record(file_path="tests/western_union/endpoints/cancel_complete.yaml")@responses.activate
def test_cancel(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/endpoints/cancel.yaml")
    ref_no, mtcn = "Y3snz233UkGt1Gw4", "0352466394"
    payment_instruction = PaymentInstruction.objects.create()
    pl = PaymentRecordLog.objects.create(parent=payment_instruction, record_code=ref_no, extra_data={"mtcn": mtcn})
    cancel(ref_no, mtcn)
    pl.refresh_from_db()
    assert pl.message, pl.success == ("Cancelled", True)
