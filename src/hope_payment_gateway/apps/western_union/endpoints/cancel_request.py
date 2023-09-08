from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import agent, get_usd, unicef


def cancel_request(pk, mtcn=None, database_key=None, reason="WIC"):
    if not mtcn:
        obj = PaymentRecord.objects.get(pk=pk)
        mtcn = obj.token_number
    frm = get_usd(obj.transaction_reference_id)
    payload = {
        "device": agent,
        "channel": unicef,
        "foreign_remote_system": frm,
        "reason_for_redelivery": reason,
        "mtcn": mtcn,
        "database_key": database_key,
        "comments_data": "Comments",
        "disallow_traffic_flag": "Y",
    }

    client = WesternUnionClient("CancelSend_Service_H2HService.wsdl")
    return client.response_context("CancelSend", payload)
