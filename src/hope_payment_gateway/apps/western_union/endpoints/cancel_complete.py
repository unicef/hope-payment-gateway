from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.cancel_request import cancel_request
from hope_payment_gateway.apps.western_union.endpoints.search_request import search_request


def cancel_complete(pk, mtcn=None):
    obj = PaymentRecord.objects.get(pk=pk)
    response = search_request(pk, mtcn)
    payload = response["content"]
    try:
        database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
    except TypeError:
        return {"title": "Missing Database Key", "content": response, "format": format, "code": 500}
    response = cancel_request(pk, mtcn, database_key=database_key)
    if response["code"] == 200:
        obj.status = PaymentRecord.STATUS_PENDING
        obj.save()
    return response
