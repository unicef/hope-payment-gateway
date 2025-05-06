import logging

from constance import config
from requests import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.exceptions import PayloadMissingKeyError
from hope_payment_gateway.apps.fsp.utils import get_phone_number
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


class PalPayClient(FSPClient, metaclass=Singleton):
    def __init__(self):
        pass

    def prepare_transaction(self, base_payload):
        """Prepare the payload to create transactions."""
        try:
            transaction_id = base_payload["payment_record_code"]

            raw_phone_no = base_payload.get("phone_no", "N/A")
            phone_number, country_code = get_phone_number(raw_phone_no)

            payload = {
                "first_name": base_payload["first_name"],
                "last_name": base_payload["last_name"],
                "amount": base_payload["amount"],
                "phone": phone_number,
            }
        except KeyError as e:
            raise PayloadMissingKeyError(f"InvalidPayload: {e.args[0]} is missing in the payload")
        return transaction_id, payload

    def create_transaction(self, base_payload, update=True):
        """Create a transaction to MoneyGram."""
        endpoint = "/disbursement/v1/transactions"
        record_code = base_payload["payment_record_code"]
        pr = PaymentRecord.objects.get(
            record_code=record_code,
            parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        )
        flow = PaymentRecordFlow(pr)
        try:
            transaction_id, payload = self.prepare_transaction(base_payload)
            response = self.perform_request(endpoint, transaction_id, payload, "post")
        except (PayloadMissingKeyError, ValueError, TypeError) as e:
            pr.message = e.args[0]
            response = Response(
                {"context": [{"code": "validation_error", "message": e.args[0]}]},
                status=HTTP_400_BAD_REQUEST,
            )
            payload = response
        if response.status_code >= 300:
            pr.message = ", ".join(response.text)
            flow.fail()
            pr.success = False
            response = Response(response.data, status=HTTP_400_BAD_REQUEST)
        else:
            pr.success = True
        pr.save()
        if update and response.status_code == 200:
            self.post_transaction(response, base_payload)

        return payload, response

    def status(self, payload):
        """Query PalPay to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"/disbursement/status/v1/transactions/{transaction_id}"
        payload = {}
        return payload, self.perform_request(endpoint, transaction_id, payload)
