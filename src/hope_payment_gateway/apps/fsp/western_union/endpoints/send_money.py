import random

import phonenumbers
import sentry_sdk
from constance import config
from django_fsm import TransitionNotAllowed
from phonenumbers.phonenumberutil import NumberParseException
from zeep.helpers import serialize_object

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.config import MONEY_IN_TIME, WALLET, WMF, sender, unicef, web
from hope_payment_gateway.apps.fsp.western_union.endpoints.helpers import integrate_payload
from hope_payment_gateway.apps.fsp.western_union.exceptions import InvalidCorridor, PayloadException, PayloadMissingKey
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import PaymentRecord


def create_validation_payload(hope_payload):
    for key in ["first_name", "last_name", "amount", "destination_country", "destination_currency"]:
        if not (key in hope_payload.keys() and hope_payload[key]):
            raise PayloadMissingKey("InvalidPayload: {} is missing in the payload".format(key))

    counter_ids = hope_payload.get("counter_id", "N/A")
    counter_id = random.choice(counter_ids) if isinstance(counter_ids, list) else counter_ids
    transaction_type = hope_payload.get("transaction_type", WMF)
    frm = {
        "identifier": hope_payload.get("identifier", "N/A"),
        "reference_no": hope_payload.get("payment_record_code", "N/A"),
        "counter_id": counter_id,
    }
    raw_phone_no = hope_payload.get("phone_no", "N/A")
    try:
        phone_no = phonenumbers.parse(raw_phone_no, None)
        phone_number = phone_no.national_number
        country_code = phone_no.country_code
    except NumberParseException:
        phone_number = raw_phone_no
        country_code = None

    receiver = {
        "name": {
            "first_name": hope_payload["first_name"],
            "last_name": hope_payload["last_name"],
            # "first_name": str(hope_payload["first_name"].encode("utf-8"))[2:-1],
            # "last_name": str(hope_payload["last_name"].encode("utf-8"))[2:-1],
            "name_type": "D",
        },
        "contact_phone": phone_number,
        "mobile_phone": {
            "phone_number": {
                "country_code": country_code,
                "national_number": phone_number,
            },
        },
        "reason_for_sending": hope_payload.get("reason_for_sending", None),
    }
    amount_key = "destination_principal_amount" if transaction_type == WMF else "originators_principal_amount"
    financials = {
        amount_key: int(float(hope_payload["amount"]) * 100),
    }
    payment_details = {
        "recording_country_currency": {  # sending country
            "iso_code": {
                "country_code": hope_payload.get("origination_country", "US"),
                "currency_code": hope_payload.get("origination_currency", "USD"),
            },
        },
        "destination_country_currency": {  # destination
            "iso_code": {
                "country_code": hope_payload["destination_country"],
                "currency_code": hope_payload["destination_currency"],
            },
        },
        "originating_country_currency": {  # sending country
            "iso_code": {
                "country_code": hope_payload.get("origination_country", "US"),
                "currency_code": hope_payload.get("origination_currency", "USD"),
            },
        },
        "transaction_type": transaction_type,
        "payment_type": "Cash",
        "duplicate_detection_flag": hope_payload.get("duplication_enabled", "D"),
        # needed for US and MEX
        # "expected_payout_location": {
        #     "state_code": "NY",
        #     "city": "New York"
        # }
    }

    delivery_services = {"code": hope_payload.get("delivery_services_code", MONEY_IN_TIME)}
    partner_notification = {"partner_notification": {"notification_requested": "Y"}}

    payload = {
        "device": web,
        "channel": unicef,
        "sender": sender,
        "receiver": receiver,
        "payment_details": payment_details,
        "financials": financials,
        "delivery_services": delivery_services,
        "foreign_remote_system": frm,
        "partner_info_buffer": partner_notification,
        "wallet_details": {"service_provider_code": hope_payload.get("service_provider_code", None)},
    }

    if "delivery_services_code" in hope_payload and hope_payload["delivery_services_code"] == WALLET:
        country = hope_payload["destination_country"]
        currency = hope_payload["destination_currency"]
        try:
            template = Corridor.objects.get(
                destination_country=country,
                destination_currency=currency,
            ).template

        except Corridor.DoesNotExist:
            raise InvalidCorridor(f"Invalid corridor for {country}/{currency}")

        payload = integrate_payload(payload, template)

    return payload


def send_money_validation(payload):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    client = WesternUnionClient("SendMoneyValidation_Service_H2HService.wsdl")
    sentry_sdk.capture_message("Western Union: Send Money Validation")
    print(payload["foreign_remote_number"].get("reference_no", None))
    return client.response_context(
        "sendmoneyValidation", payload, "SendmoneyValidation_Service_H2H", f"SOAP_HTTP_Port_{wu_env}"
    )


def send_money_store(payload):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    client = WesternUnionClient("SendMoneyStore_Service_H2HService.wsdl")
    sentry_sdk.capture_message("Western Union: Send Money Store")
    print(payload.get("mtcn", None))
    return client.response_context(
        "SendMoneyStore_H2H", payload, "SendMoneyStore_Service_H2H", f"SOAP_HTTP_Port_{wu_env}"
    )


def send_money(hope_payload):
    record_code = hope_payload["payment_record_code"]
    try:
        pr = PaymentRecord.objects.get(record_code=record_code, status=PaymentRecord.PENDING)
    except PaymentRecord.DoesNotExist:
        return None
    try:
        payload = create_validation_payload(hope_payload)
        response = send_money_validation(payload)
        pr.refresh_from_db()
        if response["code"] != 200:
            pr.message = f"Validation failed: {response['error']}"
            pr.success = False
            pr.save()
            return pr
        smv_payload = serialize_object(response["content"])
        pr.auth_code = smv_payload["mtcn"]
        pr.fsp_code = smv_payload["new_mtcn"]
        pr.save()
    except (InvalidCorridor, PayloadException, TransitionNotAllowed) as exc:
        pr.message = str(exc)
        pr.status = PaymentRecord.ERROR
        pr.success = False
        pr.save()
        return pr

    if response["code"] != 200:
        pr.message = f'Send Money Validation: {response["error"]}'
        pr.success = False
        pr.auth_code = smv_payload["mtcn"]
        pr.fsp_code = smv_payload["new_mtcn"]
        if response["error"][:5] not in config.WESTERN_UNION_ERRORS.split(";"):
            pr.fail()
        pr.save()
        return pr

    extra_data = {
        key: smv_payload[key]
        for key in ["foreign_remote_system", "instant_notification", "mtcn", "new_mtcn", "financials"]
    }
    log_data = extra_data.copy()
    log_data["record_code"] = hope_payload["payment_record_code"]
    log_data.pop("financials")
    pr.message = "Send Money Validation: Success"
    pr.success = True
    pr.extra_data.update(log_data)
    pr.save()
    for key, value in extra_data.items():
        payload[key] = value

    response = send_money_store(payload)
    pr.refresh_from_db()
    if response["code"] == 200:
        pr.message, pr.success = "Send Money Store: Success", True
        pr.store()
    else:
        pr.message, pr.success = f'Send Money Store: {response["error"]}', False
        pr.fail()
    pr.extra_data.update(log_data)
    pr.save()
    return pr
