from zeep.helpers import serialize_object

from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.helpers import integrate_payload
from hope_payment_gateway.apps.western_union.endpoints.utils import MONEY_IN_TIME, WMF, get_usd, sender, unicef, web
from hope_payment_gateway.apps.western_union.models import Corridor, PaymentRecordLog


def create_validation_payload(hope_payload):
    frm = get_usd(hope_payload["payment_record_code"])

    receiver = {
        "name": {"first_name": hope_payload["first_name"], "last_name": hope_payload["last_name"], "name_type": "D"},
        "contact_phone": hope_payload["phone_no"],
        "mobile_phone": {
            "phone_number": {
                "country_code": None,
                "national_number": hope_payload["phone_no"][2:],  # fixme
            },
        },
        "reason_for_sending": hope_payload.get("reason_for_sending", None),
    }
    financials = {
        # "originators_principal_amount": amount,
        "destination_principal_amount": hope_payload["amount"],
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
                "country_code": hope_payload["destination_country"],
                "currency_code": hope_payload["destination_currency"],
            },
        },
        "originating_country_currency": {  # sending country
            "iso_code": {
                "country_code": "US",
                "currency_code": "USD",
            },
        },
        "transaction_type": hope_payload.get("transaction_type", WMF),
        "payment_type": "Cash",
        "duplicate_detection_flag": hope_payload.get("duplication_enabled", "D"),
        # needed for US and MEX
        # "expected_payout_location": {
        #     "state_code": "NY",
        #     "city": "New York"
        # }
    }

    delivery_services = {"code": hope_payload.get("delivery_services_code", MONEY_IN_TIME)}

    payload = {
        "device": web,
        "channel": unicef,
        "sender": sender,
        "receiver": receiver,
        "payment_details": payment_details,
        "financials": financials,
        "delivery_services": delivery_services,
        "foreign_remote_system": frm,
        "wallet_details": {"service_provider_code": None},
    }

    if "corridor" in hope_payload:
        # destination_country = hope_payload["destination_country"]
        template = Corridor.objects.get(description=hope_payload["corridor"]).template
        payload = integrate_payload(payload, template)

    return payload


def send_money_validation(payload):
    client = WesternUnionClient("SendMoneyValidation_Service_H2HService.wsdl")
    return client.response_context("sendmoneyValidation", payload)


def send_money_store(payload):
    client = WesternUnionClient("SendMoneyStore_Service_H2HService.wsdl")
    return client.response_context("SendMoneyStore_H2H", payload)


def send_money(hope_payload):
    payload = create_validation_payload(hope_payload)
    response = send_money_validation(payload)
    smv_payload = serialize_object(response["content"])
    record_code = hope_payload["payment_record_code"]
    log = PaymentRecordLog.objects.get(record_code=record_code)
    if response["code"] != 200:
        log.message = f'Validation Error: {response["error"]}'
        log.success = False
        log.save()
        return log

    extra_data = {key: smv_payload[key] for key in ["instant_notification", "mtcn", "new_mtcn", "financials"]}
    log_data = extra_data.copy()
    log_data["record_code"] = record_code
    log_data.pop("financials")
    log.message = "Validation Success"
    log.success = True
    log.extra_data = log_data
    log.save()
    for key, value in extra_data.items():
        payload[key] = value

    response = send_money_store(payload)
    if response["code"] == 200:
        log.message, log.success = "Store Success", True
    else:
        log.message, log.success = response["error"], False
    log.extra_data = log_data
    log.save()
    return log
