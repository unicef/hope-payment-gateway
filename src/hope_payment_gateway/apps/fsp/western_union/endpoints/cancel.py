import logging

from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.config import WIC, agent
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentRecord


def search_request(frm, mtcn):
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    partner_notification = {"partner_notification": {"notification_requested": "Y"}}
    payload.pop("sender", None)
    payload.update(
        {
            "device": agent,
            "payment_transaction": {
                "payment_details": {
                    "originating_country_currency": {"iso_code": {"country_code": "US", "currency_code": "USD"}},
                },
                "mtcn": mtcn,
            },
            "search_flag": "CANCEL_SEND",
            "foreign_remote_system": frm,
            "partner_info_buffer": partner_notification,
        }
    )
    client = WesternUnionClient("Search_Service_H2HServiceService.wsdl")
    return client.response_context("Search", payload, "Search_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def cancel_request(frm, mtcn, database_key, reason=WIC):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "device": agent,
            "foreign_remote_system": frm,
            "reason_for_redelivery": reason,
            "mtcn": mtcn,
            "database_key": database_key,
            "comments_data": "Client requested for cancel",
            "disallow_traffic_flag": "Y",
        }
    )

    client = WesternUnionClient("CancelSend_Service_H2HService.wsdl")
    ref_no = payload.get("foreign_remote_system", dict()).get("reference_no", "N/A")
    logging.info(f"CANCEL {ref_no}")
    return client.response_context("CancelSend", payload, "CancelSend_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def cancel(pk):
    pr = PaymentRecord.objects.get(pk=pk)
    mtcn = pr.extra_data.get("mtcn", None)
    frm = pr.extra_data.get("foreign_remote_system", None)
    response = search_request(frm, mtcn)
    payload = response["content"]
    try:
        database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
    except TypeError:
        database_key = None
    if not database_key:
        pr.message = "Search Error: No Money Transfer Key"
        pr.success = False
        flow = PaymentRecordFlow(pr)
        flow.fail()
        pr.save()
        return pr

    response = cancel_request(frm, mtcn, database_key)
    extra_data = {"db_key": database_key, "mtcn": mtcn}

    if response["code"] == 200:
        pr.message = "Request for cancel"
        pr.success = True
    else:
        pr.message = f"Cancel request error: {response['error']}"
        pr.success = False
    pr.extra_data.update(extra_data)
    pr.save()
    return pr


def reset_mtcns(mtcns, counter_id, identifier, reference_no):
    frm = {"counter_id": counter_id, "identifier": identifier, "reference_no": reference_no}
    for mtcn in mtcns:
        response = search_request(frm, mtcn)
        payload = response["content"]
        try:
            database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
        except TypeError:
            database_key = None
            logging.warning(f"ERROR {mtcn}")
        response = cancel_request(frm, mtcn, database_key)
        if response["code"] != 200:
            code = response["code"]
            logging.warning(f"{code} {mtcn}")
