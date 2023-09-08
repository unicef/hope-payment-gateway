from django.urls import reverse

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.cancel_request import (
    cancel_request,
)
from hope_payment_gateway.apps.western_union.endpoints.search_request import (
    search_request,
)
from hope_payment_gateway.apps.western_union.models import Log


def cancel_complete(pk, mtcn=None):
    obj = PaymentRecord.objects.get(pk=pk)
    response = search_request(pk, mtcn)
    payload = response["content"]
    try:
        database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
    except TypeError:
        return {
            "title": "Missing Database Key",
            "content": response,
            "format": format,
            "code": 500,
            "error": "DB Key Error: No Money Trasnfer Key",
        }
    response = cancel_request(pk, mtcn, database_key=database_key)
    extra_data = {"db_key": database_key, "mtcn": mtcn}
    if response["code"] == 200:
        obj.status = PaymentRecord.STATUS_PENDING
        obj.reason_for_unsuccessful_payment = f"Cancelled: DB key {database_key}"
        obj.save()
        msg = "Cancelled"
        success = True
    else:
        msg = "Cancelled KO"
        success = False
    Log.objects.create(transaction_id=obj.transaction_reference_id, message=msg, extra_data=extra_data, success=success)
    return reverse("admin:hope_paymentrecord_change", args=[obj.pk])
