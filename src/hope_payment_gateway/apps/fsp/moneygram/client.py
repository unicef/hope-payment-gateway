import base64
import json
import logging
import uuid
from urllib.parse import urlencode

from django.conf import settings

import requests
from constance import config
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.moneygram import (
    AVAILABLE,
    CLOSED,
    DELIVERED,
    IN_TRANSIT,
    RECEIVED,
    REFUNDED,
    REJECTED,
    SENT,
    UNFUNDED,
)
from hope_payment_gateway.apps.fsp.utils import (
    get_from_delivery_mechanism,
    get_phone_number,
)
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentRecord,
)

logger = logging.getLogger(__name__)


class PayloadMissingKey(Exception):
    pass


class InvalidToken(Exception):
    pass


class ExpiredToken(Exception):
    pass


class MoneyGramClient(FSPClient, metaclass=Singleton):
    token = None
    expires_in = None
    sender = None

    def __init__(self):
        self.set_token()
        self.sender = FinancialServiceProvider.objects.get(vendor_number=config.MONEYGRAM_VENDOR_NUMBER).configuration

    def set_token(self):
        """Set up the token to perform MoneyGram API calls."""
        url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
        credentials = f"{settings.MONEYGRAM_CLIENT_ID}:{settings.MONEYGRAM_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic " + encoded_credentials,
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            parsed_response = json.loads(response.text)
        except ConnectionError:
            self.token = None
        else:
            if response.status_code == 200:
                self.token = parsed_response["access_token"]
                self.expires_in = parsed_response["expires_in"]
            else:
                logger.warning("Invalid token")
                self.token = None
                error = parsed_response["error"]
                raise InvalidToken(f"{error['category']}: {error['message']}  [{error['code']}]")

    def get_headers(self, request_id):
        headers = {
            "Content-Type": "application/json",
            "X-MG-ClientRequestId": request_id,
            "content-type": "application/json",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    @staticmethod
    def get_basic_payload():
        return {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
            "userLanguage": "en-US",
        }

    def prepare_transaction(self, base_payload):
        """Prepare the payload to create transactions."""
        raw_phone_no = base_payload.get("phone_no", "N/A")
        phone_number, country_code = get_phone_number(raw_phone_no)

        for key in [
            "first_name",
            "last_name",
            "amount",
            "destination_country",
            "destination_currency",
            "payment_record_code",
        ]:
            if not (key in base_payload and base_payload[key]):
                raise PayloadMissingKey(f"InvalidPayload: {key} is missing in the payload")
        transaction_id = base_payload["payment_record_code"]
        payload = {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
            "userLanguage": "en-US",
            "destinationCountryCode": base_payload["destination_country"],
            "receiveCurrencyCode": base_payload["destination_currency"],
            "serviceOptionCode": get_from_delivery_mechanism(base_payload, "service_provider_code", "WILL_CALL"),
            "serviceOptionRoutingCode": get_from_delivery_mechanism(base_payload, "service_provider_routing_code"),
            "autoCommit": "true",
            "sendAmount": {
                "currencyCode": base_payload["origination_currency"],
                "value": base_payload["amount"],
            },
            "sender": self.sender,
            "beneficiary": {
                "consumer": {
                    "name": {
                        "firstName": base_payload["first_name"],
                        "middleName": base_payload.get("middle_name", ""),
                        "lastName": base_payload["last_name"],
                    },
                    "address": {
                        "line1": base_payload.get("address"),
                        "city": base_payload.get("city"),
                        "countryCode": base_payload["destination_country"],
                        "postalCode": base_payload.get("zip"),
                    },
                    "mobilePhone": {
                        "number": phone_number,
                        "countryDialCode": country_code,
                    },
                }
            },
            "targetAccount": {
                "accountNumber": get_from_delivery_mechanism(base_payload, "bank_account_number"),
                "bankName": get_from_delivery_mechanism(base_payload, "bank_name"),
            },
            "receipt": {
                "primaryLanguage": base_payload.get("receipt_primary_language", None),
                "secondaryLanguage": base_payload.get("receipt_secondary_language", None),
            },
        }
        return transaction_id, payload

    def create_transaction(self, base_payload, update=True):
        """Create a transaction to MoneyGram."""
        endpoint = "/disbursement/v1/transactions"
        transaction_id, payload = self.prepare_transaction(base_payload)
        response = self.perform_request(endpoint, transaction_id, payload, "post")

        if update and response.status_code == 200:
            self.post_transaction(response, base_payload)

        return response

    def prepare_quote(self, base_payload: dict):
        transaction_id = base_payload["payment_record_code"]
        payload = self.get_basic_payload()
        payload.update(
            {
                "destinationCountryCode": base_payload["destination_country"],
                "serviceOptionCode": get_from_delivery_mechanism(base_payload, "service_provider_code"),
                "beneficiaryTypeCode": "Consumer",
                "sendAmount": {
                    "currencyCode": base_payload["origination_currency"],
                    "value": base_payload["amount"],
                },
            }
        )
        return transaction_id, payload

    def quote(self, base_payload):
        """Create a quote request to MoneyGram."""
        endpoint = "/disbursement/v1/transactions/quote"
        transaction_id, payload = self.prepare_quote(base_payload)
        return self.perform_request(endpoint, transaction_id, payload, "post")

    def status(self, transaction_id):
        endpoint = f"/disbursement/status/v1/transactions/{transaction_id}"
        payload = self.get_basic_payload()
        status_transaction_id = str(uuid.uuid4())
        return self.perform_request(endpoint, status_transaction_id, payload)

    def query_status(self, transaction_id, update):
        """Query MoneyGram to get information regarding the transaction status."""
        response = self.status(transaction_id)
        if update:
            pr = PaymentRecord.objects.get(
                fsp_code=transaction_id,
                parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
            )
            update_status(pr, response.data["transactionStatus"])
            pr.payout_amount = response.data["receiveAmount"]["amount"]["value"]
            pr.save()
        return response

    def get_required_fields(self, base_payload):
        endpoint = "/reference-data/v1/transaction-fields-send"
        payload = self.get_basic_payload()
        transaction_id = str(uuid.uuid4())
        payload.update(
            {
                "destinationCountryCode": base_payload["destination_country"],
                "serviceOptionCode": get_from_delivery_mechanism(base_payload, "service_provider_code", "WILL_CALL"),
                "serviceOptionRoutingCode": get_from_delivery_mechanism(base_payload, "service_provider_routing_code"),
                "amount": base_payload["amount"],
                "sendCurrencyCode": base_payload.get("origin_currency", "USD"),
                "receiveCurrencyCode": base_payload["destination_currency"],
            }
        )
        return self.perform_request(endpoint, transaction_id, payload)

    def get_service_options(self, base_payload):
        endpoint = "/reference-data/v1/service-options"
        payload = self.get_basic_payload()
        transaction_id = str(uuid.uuid4())
        payload["destinationCountryCode"] = base_payload["destination_country"]
        return self.perform_request(endpoint, transaction_id, payload)

    def perform_request(self, endpoint, transaction_id, payload, method="get"):
        response = None
        base_url = settings.MONEYGRAM_HOST + endpoint
        for _ in range(2):
            try:
                headers = self.get_headers(transaction_id)
                if method == "get":
                    url = base_url + "?" + urlencode(payload)
                    response = requests.get(url, headers=headers, timeout=30)
                else:
                    request_method = getattr(requests, method)
                    response = request_method(base_url, json=payload, headers=headers, timeout=30)
                response = Response(response.json(), response.status_code)
                if response.status_code == 200:
                    break
                else:
                    self.set_token()
            except (
                requests.exceptions.RequestException,
                requests.exceptions.MissingSchema,
            ):
                logger.error("An error occurred")
                self.set_token()
        if not response:
            logger.error("Cannot retrieve response")
        elif response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}")
        return response

    def post_transaction(self, response, payload):
        """Update record in the database."""
        body = response.data
        record_code = payload["payment_record_code"]
        pr = PaymentRecord.objects.get(
            record_code=record_code,
            parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
        )
        if "errors" in body:
            return Response(body, status=HTTP_400_BAD_REQUEST)
        pr.auth_code = body["referenceNumber"]
        pr.fsp_code = body["transactionId"]
        pr.success = True

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
        except TransitionNotAllowed:
            response = Response(
                {"errors": [{"error": "transition_not_allowed"}]},
                status=HTTP_400_BAD_REQUEST,
            )
        return response

    def refund(self, transaction_id, base_payload):
        endpoint = f"/disbursement/refund/v1/transactions/{transaction_id}"
        payload = self.get_basic_payload()
        status_transaction_id = str(uuid.uuid4())
        payload["refundReasonCode"] = base_payload.get("refuse_reason_code")
        resp = self.perform_request(endpoint, status_transaction_id, payload)
        if resp.status_code == 200:
            pr = PaymentRecord.objects.get(
                fsp_code=transaction_id,
                parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
            )
            pr.message = "Request per REFUND"
            pr.save()
            payload = self.get_basic_payload()
            payload["refundId"] = resp.data["refundId"]

            endpoint = f"/disbursement/refund/v1/transactions/{transaction_id}/commit"
            status_transaction_id = str(uuid.uuid4())
            resp = self.perform_request(endpoint, status_transaction_id, payload, "put")
            if resp.status_code == 200:
                pr.message = "Refunded"
                pr.extra_data.update({"refund_reference": payload["refundId"]})
                update_status(pr, REFUNDED)
                pr.save()
        return resp


def update_status(pr, status):
    if pr.status != status:
        flow = PaymentRecordFlow(pr)
        pr.success = False
        if status in [UNFUNDED, AVAILABLE]:
            pass
        elif status in [SENT, IN_TRANSIT]:
            flow.store()
            pr.success = True
        elif status in [RECEIVED, DELIVERED]:
            pr.success = True
            flow.confirm()
        elif status in [REJECTED]:
            flow.purge()
        elif status in [REFUNDED]:
            flow.refund()
        elif status in [CLOSED]:
            flow.fail()
        else:
            flow.fail()
        pr.save()
