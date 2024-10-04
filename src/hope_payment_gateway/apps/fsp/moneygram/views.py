from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord


def quote_transaction(payload):
    client = MoneyGramClient()
    response = client.quote(payload)
    return response


def create_transaction(payload):
    client = MoneyGramClient()
    response = client.create_transaction(payload)
    if response:
        body = response.json()
        record_code = payload["payment_record_code"]
        pr = PaymentRecord.objects.get(record_code=record_code)
        pr.fsp_code = body["referenceNumber"]
        pr.success = True
        pr.payout_amount = body["receiveAmount"]["amount"]["value"]
        pr.extra_data.update(
            {
                "fee": body["receiveAmount"]["fees"]["value"],
                "fee_currency": body["receiveAmount"]["fees"]["currencyCode"],
                "taxes": body["receiveAmount"]["taxes"]["value"],
                "taxes_currency": body["receiveAmount"]["taxes"]["currencyCode"],
                "expectedPayoutDate": body["expectedPayoutDate"],
                "transactionId": body["transactionId"],
            }
        )
        try:
            flow = PaymentRecordFlow(pr)
            flow.store()
        except TransitionNotAllowed as e:
            response = Response({"transition_not_allowed": str(e)}, status=HTTP_400_BAD_REQUEST)
        return response
