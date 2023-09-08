from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import agent, get_usd, unicef


def search_request(pk, mtcn=None):
    obj = PaymentRecord.objects.get(pk=pk)
    if not mtcn:
        mtcn = obj.token_number
    frm = get_usd(obj.unicef_id)
    payload = {
        "device": agent,
        "channel": unicef,
        "payment_transaction": {
            "payment_details": {
                "originating_country_currency": {"iso_code": {"country_code": "US", "currency_code": "USD"}},
            },
            "mtcn": mtcn,
        },
        "search_flag": "CANCEL_SEND",
        "foreign_remote_system": frm,
    }
    client = WesternUnionClient("Search_Service_H2HServiceService.wsdl")
    return client.response_context("Search", payload)
