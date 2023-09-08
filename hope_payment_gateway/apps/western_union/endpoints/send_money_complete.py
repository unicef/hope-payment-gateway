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
from hope_payment_gateway.apps.western_union.models import Corridor, Log


def send_money_complete(pk, wallet=None):
    obj = PaymentRecord.objects.get(pk=pk)
    if obj.status != PaymentRecord.STATUS_PENDING:
        return {"title": "The Payment Record is not in status Pending", "code": 400}
    if hasattr(obj, "household_snapshot"):
        snapshot_data = obj.household_snapshot
    else:
        # raise MissingHousehold
        snapshot_data = snapshot_example
    frm = get_usd(obj.unicef_id)
    transaction_id = frm["reference_no"]

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
                "country_code": source_country,
                "currency_code": source_currency,
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
        # 'wallet_details': {"service_provider_code": "06301"},
        "foreign_remote_system": frm,
    }

    if wallet:
        print("Amending Payload")
        corridor = Corridor.objects.get(id=wallet)
        payload = integrate_payload(payload, corridor.template)
        print(payload)

    response = send_money_validation(pk, payload)
    if response["code"] != 200:
        obj.status = PaymentRecord.STATUS_VALIDATION_KO
        obj.reason_for_unsuccessful_payment = response["error"]
        obj.save()
        Log.objects.create(
            transaction_id=transaction_id, message=f'Validation Error: {response["error"]}', success=False
        )
        return reverse("admin:hope_paymentrecord_change", args=[obj.pk])

    obj.status = PaymentRecord.STATUS_VALIDATION_OK
    obj.transaction_reference_id = transaction_id
    obj.token_number = response["content"]["mtcn"]  # fixme
    obj.save()
    content = serialize_object(response["content"])
    extra_data = {key: content[key] for key in ["instant_notification", "mtcn", "new_mtcn", "financials"]}

    Log.objects.create(
        transaction_id=obj.transaction_reference_id, message="Validation Success", extra_data=extra_data, success=True
    )
    for key, value in extra_data.items():
        payload[key] = value

    response = send_money_store(pk, payload)
    if response["code"] == 200:
        obj.status = PaymentRecord.STATUS_SUCCESS
        msg = "Store Success"
        success = True
        extra_data = {}
    else:
        obj.status = PaymentRecord.STATUS_ERROR
        obj.reason_for_unsuccessful_payment = response["error"]
        msg = response["error"]
        success = False
        extra_data = {"mtcn": obj.transaction_reference_id, "message_code": f'Store Error: {response["error"]}'}
    obj.save()
    Log.objects.create(transaction_id=obj.transaction_reference_id, message=msg, extra_data=extra_data, success=success)
    return reverse("admin:hope_paymentrecord_change", args=[obj.pk])
