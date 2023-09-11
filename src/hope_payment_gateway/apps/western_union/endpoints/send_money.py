from zeep.helpers import serialize_object

from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import get_usd, sender, unicef, web
from hope_payment_gateway.apps.western_union.models import PaymentRecordLog


def create_validation_payload(hope_payload):
    frm = get_usd(hope_payload["payment_record_code"])

    receiver = {
        "name": {"first_name": hope_payload["first_name"], "last_name": hope_payload["last_name"], "name_type": "D"},
        # "email": email,
        "contact_phone": hope_payload["phone_no"],
        # "mobile_phone": {
        #     "phone_number": {
        #         "country_code": "1",
        #         "national_number": phone_no,
        #     },
        # },
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
                "country_code": hope_payload["source_country"],
                "currency_code": hope_payload["source_currency"],
            },
        },
        "transaction_type": hope_payload["transaction_type"],
        "payment_type": "Cash",
        "duplicate_detection_flag": hope_payload["duplication_enabled"],
        # needed for US and MEX
        # "expected_payout_location": {
        #     "state_code": "NY",
        #     "city": "New York"
        # }
    }

    delivery_services = {"code": hope_payload["delivery_services_code"]}

    return {
        "device": web,
        "channel": unicef,
        "sender": sender,
        "receiver": receiver,
        "payment_details": payment_details,
        "financials": financials,
        "delivery_services": delivery_services,
        "foreign_remote_system": frm,
    }


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
    log, _ = PaymentRecordLog.objects.get_or_create(record_code=record_code)
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
