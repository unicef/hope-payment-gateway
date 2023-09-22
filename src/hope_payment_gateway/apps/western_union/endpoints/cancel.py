from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.config import WIC, agent, get_usd, unicef
from hope_payment_gateway.apps.western_union.models import PaymentRecord


def search_request(record_code, mtcn):
    frm = get_usd(record_code)
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


def cancel_request(record_code, mtcn, database_key, reason=WIC):
    frm = get_usd(record_code)
    payload = {
        "device": agent,
        "channel": unicef,
        "foreign_remote_system": frm,
        "reason_for_redelivery": reason,
        "mtcn": mtcn,
        "database_key": database_key,
        "comments_data": "Cancelled by UNICEF",
        "disallow_traffic_flag": "Y",
    }

    client = WesternUnionClient("CancelSend_Service_H2HService.wsdl")
    return client.response_context("CancelSend", payload)


def cancel(record_uuid, mtcn):
    log = PaymentRecord.objects.get(uuid=record_uuid)
    response = search_request(log.record_code, mtcn)
    payload = response["content"]
    try:
        database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
    except TypeError:
        database_key = None
    if not database_key:
        log.message = "Search Error: No Money Transfer Key"
        log.success = False
        log.fail()
        log.save()
        return log

    response = cancel_request(log.record_code, mtcn, database_key)
    extra_data = {"db_key": database_key, "mtcn": mtcn}

    if response["code"] == 200:
        log.message = "Cancelled"
        log.success = True
        log.cancel()
    else:
        log.message = "Cancel error"
        log.success = False
        log.store()
    log.extra_data.update(extra_data)
    log.save()
    return log