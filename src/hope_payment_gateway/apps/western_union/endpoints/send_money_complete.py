from zeep.helpers import serialize_object

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.send_money_store import send_money_store
from hope_payment_gateway.apps.western_union.endpoints.send_money_validation import send_money_validation
from hope_payment_gateway.apps.western_union.endpoints.utils import (
    MONEY_IN_TIME,
    WALLET,
    WMF,
    get_usd,
    sender,
    snapshot_example,
    unicef,
    web,
)


def send_money_complete(pk, wallet_no=None):
    obj = PaymentRecord.objects.get(pk=pk)
    if obj.status != PaymentRecord.STATUS_PENDING:
        return {"title": "The Payment Record is not in status Pending", "code": 400}
    if hasattr(obj, "household_snapshot"):
        snapshot_data = obj.household_snapshot
    else:
        # raise MissingHousehold
        snapshot_data = snapshot_example
    frm = get_usd(obj.unicef_id)

    collector = snapshot_data["primary_collector"]
    first_name = collector["given_name"]
    last_name = collector["family_name"]
    phone_no = collector["phone_no"]
    source_country = "US"
    source_currency = "USD"
    transaction_type = WMF
    destination_country = "EC"  # core countrycodemap
    destination_currency = obj.currency
    duplication_enabled = "D"
    amount = int(obj.entitlement_quantity * 100)
    delivery_services_code = WALLET if wallet_no else MONEY_IN_TIME

    receiver = {
        "name": {"first_name": first_name, "last_name": last_name, "name_type": "D"},
        "contact_phone": phone_no,
    }
    financials = {
        # "originators_principal_amount": amount_with_fee,
        "destination_principal_amount": amount,
    }
    payment_details = {
        "recording_country_currency": {  # sending country
            "iso_code": {
                "country_code": "US",
                "currency_code": "USD",
            },
        },
        "destination_country_currency": {  # destination
            "iso_code": {
                "country_code": destination_country,
                "currency_code": destination_currency,
            },
        },
        "originating_country_currency": {  # sending country
            "iso_code": {
                "country_code": source_country,
                "currency_code": source_currency,
            },
        },
        "transaction_type": transaction_type,
        "payment_type": "Cash",
        "duplicate_detection_flag": duplication_enabled,
    }

    delivery_services = {"code": delivery_services_code}

    payload = {
        "device": web,
        "channel": unicef,
        "sender": sender,
        "receiver": receiver,
        "payment_details": payment_details,
        "financials": financials,
        "delivery_services": delivery_services,
        "foreign_remote_system": frm,
    }

    response = send_money_validation(pk, payload)
    if response["code"] != 200:
        obj.status = PaymentRecord.STATUS_VALIDATION_KO
        obj.save()
        return response

    obj.status = PaymentRecord.STATUS_VALIDATION_OK
    obj.transaction_reference_id = response["content"]["mtcn"]
    obj.save()
    content = serialize_object(response["content"])

    for key, value in content.items():
        if key in [
            "instant_notification",
            "mtcn",
            "new_mtcn",
            "financials",
        ]:
            payload[key] = value

    response = send_money_store(pk, payload)
    if response["code"] == 200:
        obj.status = PaymentRecord.STATUS_STORE_OK
    else:
        obj.status = PaymentRecord.STATUS_STORE_KO
    obj.save()
    return response
