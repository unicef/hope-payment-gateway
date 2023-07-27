from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import agent, unicef, usd


def cancel_request(pk, mtcn="8552593921", reason="WIC", database_key="1436241538"):
    if not mtcn:
        obj = PaymentRecord.objects.get(pk=pk)
        mtcn = obj.transaction_reference_id

    payload = {
        "device": agent,
        "channel": unicef,
        "foreign_remote_system": usd,
        "reason_for_redelivery": reason,
        "mtcn": mtcn,
        "database_key": database_key,
        "comments_data": "Comments",
        "disallow_traffic_flag": "Y",
    }

    client = WesternUnionClient("CancelSend_Service_H2HService.wsdl")
    return client.response_context("CancelSend", payload)
