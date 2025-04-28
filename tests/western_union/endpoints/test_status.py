import responses
from constance.test import override_config
from factories import PaymentRecordFactory

from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


# @_recorder.record(file_path="tests/western_union/endpoints/status.yaml")
@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_status(django_app, admin_user, wu):
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
    resp = WesternUnionClient().status(pr.fsp_code, True)
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
    assert (resp["title"], resp["code"]) == ("PayStatus", 200)
