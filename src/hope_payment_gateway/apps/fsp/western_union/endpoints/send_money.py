from django_fsm import TransitionNotAllowed
from zeep.helpers import serialize_object

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.config import MONEY_IN_TIME, WMF, sender, unicef, web
from hope_payment_gateway.apps.fsp.western_union.endpoints.helpers import integrate_payload
from hope_payment_gateway.apps.fsp.western_union.exceptions import InvalidCorridor, PayloadException
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import PaymentRecord


def create_validation_payload(hope_payload):
    frm = {
        "identifier": hope_payload.get("identifier", "N/A"),
        "reference_no": hope_payload.get("payment_record_code", "N/A"),
        "counter_id": hope_payload.get("counter_id", "N/A"),
    }
    print(frm, 111)
    receiver = {
        "name": {"first_name": hope_payload["first_name"], "last_name": hope_payload["last_name"], "name_type": "D"},
        "contact_phone": hope_payload["phone_no"],
        "mobile_phone": {
            "phone_number": {
                "country_code": None,
                "national_number": hope_payload["phone_no"][1:],  # fixme
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
        try:
            country = hope_payload["destination_country"]
            currency = hope_payload["destination_currency"]
            template = Corridor.objects.get(
                destination_country=country,
                destination_currency=currency,
            ).template
        except Corridor.DoesNotExist:
            raise InvalidCorridor(f"Invalid corridor for {country}/{currency}")

        payload = integrate_payload(payload, template)

    return payload


def send_money_validation(payload):
    client = WesternUnionClient("SendMoneyValidation_Service_H2HService.wsdl")
    return client.response_context("sendmoneyValidation", payload)


def send_money_store(payload):
    client = WesternUnionClient("SendMoneyStore_Service_H2HService.wsdl")
    return client.response_context("SendMoneyStore_H2H", payload)


def send_money(hope_payload):
    record_uuid = hope_payload["record_uuid"]
    pr = PaymentRecord.objects.get(uuid=record_uuid)

    try:
        payload = create_validation_payload(hope_payload)
        response = send_money_validation(payload)
        smv_payload = serialize_object(response["content"])
        pr.validate()
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
        pr.fail()
        pr.save()
        return pr

    extra_data = {key: smv_payload[key] for key in ["instant_notification", "mtcn", "new_mtcn", "financials"]}
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
    if response["code"] == 200:
        pr.message, pr.success = "Send Money Store: Success", True
        pr.store()
    else:
        pr.message, pr.success = f'Send Money Store: {response["error"]}', False
        pr.fail()
    pr.extra_data.update(log_data)
    pr.save()
    return pr
