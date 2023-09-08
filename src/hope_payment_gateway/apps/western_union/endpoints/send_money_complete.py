from django.urls import reverse

from zeep.helpers import serialize_object

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.helpers import integrate_payload
from hope_payment_gateway.apps.western_union.endpoints.send_money_store import (
    send_money_store,
)
from hope_payment_gateway.apps.western_union.endpoints.send_money_validation import (
    send_money_validation,
)
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
from hope_payment_gateway.apps.western_union.models import Corridor


def send_money_complete(pk, wallet=1):
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
    destination_country = "PH"  # core countrycodemap
    destination_currency = "PHP"  # obj.currency
    duplication_enabled = "D"
    amount = int(obj.entitlement_quantity * 100)
    delivery_services_code = WALLET if wallet else MONEY_IN_TIME

    receiver = {
        "name": {"first_name": first_name, "last_name": last_name, "name_type": "D"},
        "contact_phone": phone_no,
        "reason_for_sending": "P020",
        # "mobile_phone": {"phone_number": {"country_code": 63, "national_number": 123412}}  # remove me
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
        # 'wallet_details': {"service_provider_code": "06301"}
    }

    if wallet:
        print("Amending Payload")
        corridor = Corridor.objects.get(id=wallet)
        payload = integrate_payload(payload, corridor.template)
        print(payload)

    response = send_money_validation(pk, payload)
    if response["code"] != 200:
        print(response)
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
    return reverse("admin:hope_paymentrecord_change", args=[obj.pk])
