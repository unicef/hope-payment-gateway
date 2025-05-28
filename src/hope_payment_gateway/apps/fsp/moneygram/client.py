import base64
import json
import logging
import uuid
from urllib.parse import urlencode

import requests
from constance import config
from django.conf import settings
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.exceptions import InvalidTokenError, PayloadMissingKeyError
from hope_payment_gateway.apps.fsp.moneygram import (
    AVAILABLE,
    CLOSED,
    DELIVERED,
    IN_TRANSIT,
    RECEIVED,
    REFUND_CHOICES,
    REFUNDED,
    REJECTED,
    SENT,
    UNFUNDED,
)
from hope_payment_gateway.apps.fsp.utils import extrapolate_errors, get_phone_number, get_account_field
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentRecord,
    PaymentRecordState,
)

logger = logging.getLogger(__name__)


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
                raise InvalidTokenError(f"{error['category']}: {error['message']}  [{error['code']}]")

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
    def get_basic_payload(agent_partner_id):
        return {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": agent_partner_id,
            "userLanguage": "en-US",
        }

    def prepare_transaction(self, base_payload):
        """Prepare the payload to create transactions."""
        raw_phone_no = base_payload.get("phone_no", "N/A")
        phone_number, country_code = get_phone_number(raw_phone_no)

        try:
            transaction_id = base_payload["payment_record_code"]

            first_name, rest = (
                base_payload["first_name"][:20],
                base_payload["first_name"][20:40],
            )
            middle_name = base_payload.get("middle_name", rest)
            last_name, rest_ln = (
                base_payload["last_name"][:20],
                base_payload["last_name"][20:40],
            )
            second_last_name = base_payload.get("second_last_name", rest_ln)

            name = {
                "firstName": first_name,
                "lastName": last_name,
            }
            if middle_name:
                name["middleName"] = middle_name
            if second_last_name:
                name["second_last_name"] = second_last_name
            payload = {
                "targetAudience": "AGENT_FACING",
                "agentPartnerId": base_payload["agent_partner_id"],
                "userLanguage": "en-US",
                "destinationCountryCode": base_payload["destination_country"],
                "sendCurrencyCode": base_payload.get("origination_currency", "USD"),
                "serviceOptionCode": base_payload.get("service_provider_code", "WILL_CALL"),
                "serviceOptionRoutingCode": base_payload.get("service_provider_routing_code"),
                "autoCommit": "true",
                "receiveAmount": {
                    "currencyCode": base_payload.get("destination_currency", "USD"),
                    "value": base_payload["amount"],
                },
                "sender": self.sender,
                "beneficiary": {
                    "consumer": {
                        "name": name,
                        "mobilePhone": {
                            "number": phone_number,
                            "countryDialCode": country_code,
                        },
                    }
                },
                "targetAccount": {
                    "accountNumber": get_account_field(base_payload, "number"),
                    "bankName": get_account_field(base_payload, "code"),
                },
                "receipt": {
                    "primaryLanguage": base_payload.get("receipt_primary_language", None),
                    "secondaryLanguage": base_payload.get("receipt_secondary_language", None),
                },
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
            status=PaymentRecordState.PENDING,
            parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
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
            pr.message = ", ".join(extrapolate_errors(response.data))
            flow.fail()
            pr.success = False
            response = Response(response.data, status=HTTP_400_BAD_REQUEST)
        else:
            pr.success = True
        pr.save()
        if update and response.status_code == 200:
            self.post_transaction(response, base_payload)

        return payload, response, endpoint

    def prepare_quote(self, base_payload: dict):
        transaction_id = base_payload["payment_record_code"]
        payload = self.get_basic_payload(base_payload["agent_partner_id"])
        payload.update(
            {
                "destinationCountryCode": base_payload["destination_country"],
                "serviceOptionCode": base_payload.get("service_provider_code"),
                "beneficiaryTypeCode": "Consumer",
                "receiveAmount": {
                    "currencyCode": base_payload.get("destination_currency", "USD"),
                    "value": base_payload["amount"],
                },
            }
        )
        return transaction_id, payload

    def quote(self, base_payload):
        """Create a quote request to MoneyGram."""
        endpoint = "/disbursement/v1/transactions/quote"
        transaction_id, payload = self.prepare_quote(base_payload)
        return payload, self.perform_request(endpoint, transaction_id, payload, "post"), endpoint

    def status(self, payload):
        """Query MoneyGram to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        agent_partner_id = payload["agent_partner_id"]
        transaction_id = record.fsp_code
        endpoint = f"/disbursement/status/v1/transactions/{transaction_id}"
        payload = self.get_basic_payload(agent_partner_id)
        status_transaction_id = str(uuid.uuid4())
        return payload, self.perform_request(endpoint, status_transaction_id, payload), endpoint

    def status_update(self, payload):
        """Query MoneyGram to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        payload, response, endpoint = self.status(payload)
        pr = PaymentRecord.objects.get(
            fsp_code=transaction_id,
            parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
        )
        update_status(pr, response.data["transactionStatus"])
        pr.payout_amount = response.data["receiveAmount"]["amount"]["value"]
        pr.save()
        return payload, response, endpoint

    def get_required_fields(self, base_payload):
        endpoint = "/reference-data/v1/transaction-fields-send"
        payload = self.get_basic_payload(base_payload["agent_partner_id"])
        transaction_id = str(uuid.uuid4())
        payload.update(
            {
                "destinationCountryCode": base_payload["destination_country"],
                "serviceOptionCode": base_payload.get("service_provider_code", "WILL_CALL"),
                "serviceOptionRoutingCode": base_payload.get("service_provider_routing_code"),
                "amount": base_payload["amount"],
                "sendCurrencyCode": base_payload.get("origination_currency", "USD"),
                "receiveCurrencyCode": base_payload["destination_currency"],
            }
        )
        return payload, self.perform_request(endpoint, transaction_id, payload), endpoint

    def get_service_options(self, base_payload):
        endpoint = "/reference-data/v1/service-options"
        payload = self.get_basic_payload(base_payload["agent_partner_id"])
        transaction_id = str(uuid.uuid4())
        payload["destinationCountryCode"] = base_payload["destination_country"]
        return payload, self.perform_request(endpoint, transaction_id, payload), endpoint

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
                "fee": f"{body['receiveAmount']['fees']['value']} {body['receiveAmount']['fees']['currencyCode']}",
                "taxes": f"{body['receiveAmount']['taxes']['value']} {body['receiveAmount']['taxes']['currencyCode']}",
                "fx_rate": f"{body['receiveAmount']['fxRate']} (estimated {body['receiveAmount']['fxRateEstimated']}",
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

    def refund(self, base_payload):
        record = PaymentRecord.objects.get(record_code=base_payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"/disbursement/refund/v1/transactions/{transaction_id}"
        payload = self.get_basic_payload(base_payload["agent_partner_id"])
        status_transaction_id = str(uuid.uuid4())
        payload["refundReasonCode"] = base_payload["refuse_reason_code"]
        reason = dict(REFUND_CHOICES).get(payload["refundReasonCode"], "-")

        resp = self.perform_request(endpoint, status_transaction_id, payload)
        if resp.status_code == 200:
            pr = PaymentRecord.objects.get(
                fsp_code=transaction_id,
                parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
            )
            pr.message = f"Request per REFUND {reason}"
            pr.save()
            payload = self.get_basic_payload(base_payload["agent_partner_id"])
            payload["refundId"] = resp.data["refundId"]

            endpoint = f"/disbursement/refund/v1/transactions/{transaction_id}/commit"
            status_transaction_id = str(uuid.uuid4())
            resp = self.perform_request(endpoint, status_transaction_id, payload, "put")
            if resp.status_code == 200:
                pr.message = f"Refunded {reason}"
                pr.extra_data.update({"refund_reference": payload["refundId"]})
                update_status(pr, REFUNDED)
                pr.save()
        return payload, resp, endpoint


def update_status(pr, status):
    mg_enabled_transaction = {
        PaymentRecordState.PENDING: [SENT, AVAILABLE, IN_TRANSIT, CLOSED],
        PaymentRecordState.TRANSFERRED_TO_FSP: [RECEIVED, DELIVERED, REJECTED, REFUNDED, CLOSED],
        PaymentRecordState.TRANSFERRED_TO_BENEFICIARY: [CLOSED],
        PaymentRecordState.CANCELLED: [],
        PaymentRecordState.REFUND: [],
        PaymentRecordState.PURGED: [],
        PaymentRecordState.ERROR: [],
    }
    if status in mg_enabled_transaction[pr.status]:
        flow = PaymentRecordFlow(pr)
        if status in [UNFUNDED]:
            pass
        elif status in [SENT, AVAILABLE, IN_TRANSIT]:
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
        pr.save()
