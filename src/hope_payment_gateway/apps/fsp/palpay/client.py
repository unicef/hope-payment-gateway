import logging
from urllib.parse import urlencode

import requests
from constance import config
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.palpay.utils import generate_hmac_signature
from hope_payment_gateway.apps.fsp.utils import get_phone_number
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    PaymentRecord,
    FinancialServiceProviderConfig,
    PaymentRecordState,
)
from django.conf import settings

logger = logging.getLogger(__name__)


class PayloadMissingKeyError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class PalPayClient(FSPClient):
    def perform_request(self, endpoint, method, payload=None):
        headers = {
            "Authorization": generate_hmac_signature(
                endpoint,
                method.upper(),
                settings.PALPAY_CLIENT_ID,
                settings.PALPAY_CLIENT_SECRET,
            ),
            "Content-Type": "application/json",
        }
        base_url = settings.PALPAY_HOST + endpoint
        if method in ["get", "GET"]:
            payload = payload or {}
            url = base_url + "?" + urlencode(payload)
            response = requests.get(url, headers=headers, timeout=30)
        else:
            request_method = getattr(requests, method)
            response = request_method(base_url, json=payload, headers=headers, timeout=30)

        return response

    def get_profile(self, payload=None):
        endpoint = "/api/v1/moneytransfer/profile"
        return None, self.perform_request(endpoint, "get"), endpoint

    def balance(self, payload=None):
        endpoint = "/api/v1/moneytransfer/check-balance"
        return None, self.perform_request(endpoint, "get"), endpoint

    def beneficiary(self, payload=None):
        endpoint = "/api/v1/moneytransfer/beneficiary"
        return None, self.perform_request(endpoint, "get"), endpoint

    def transactions(self, payload=None):
        endpoint = "/api/v1/moneytransfer/transactions"
        return None, self.perform_request(endpoint, "get"), endpoint

    def prepare_transaction(self, base_payload):
        """Prepare the payload to create transactions."""
        raw_phone_no = base_payload.get("phone_no", "N/A")
        phone_number, country_code = get_phone_number(raw_phone_no)
        transaction_id = base_payload["payment_record_code"]

        pr = PaymentRecord.objects.get(
            record_code=transaction_id,
            parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        )
        configuration = FinancialServiceProviderConfig.objects.get(
            office=pr.parent.office, fsp__vendor_number=config.PALPAY_VENDOR_NUMBER
        ).configuration

        full_name = " ".join(
            [
                base_payload[value]
                for value in [
                    "first_name",
                    "middle_name",
                    "last_name",
                    "second_last_name",
                ]
                if base_payload.get(value)
            ]
        )
        try:
            payload = {
                "profileId": configuration.get("ProfileId"),
                "transferName": transaction_id,
                "continueTransIfNotHasWallet": configuration.get("continue_if_not_has_wallet", True),
                "continueTransIfSkipLimitAmount": configuration.get("continue_if_skip_limit_amount", True),
                "beneficiary": [
                    {
                        "accountOwnerCode": "123456",
                        "fullName": full_name,
                        "natNum": base_payload["account-national_number"],
                        "mobile": phone_number,
                        "cityName": base_payload["account-city_name"],
                        "govName": base_payload["account-gov_name"],
                        "salaryAmount": base_payload["amount"],
                    }
                ],
            }

        except KeyError as e:
            raise PayloadMissingKeyError(f"InvalidPayload: {e.args[0]} is missing in the payload")
        return transaction_id, payload

    def create_transaction(self, base_payload, update=True):
        """Create a transaction to PalPay."""
        reference_number = base_payload.get("payment_record_code")
        endpoint = f"/api/v1/moneytransfer/transfer/{reference_number}"

        record_code = base_payload["payment_record_code"]
        pr = PaymentRecord.objects.get(
            record_code=record_code,
            parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        )
        if pr.status != PaymentRecordState.PENDING:
            raise TransitionNotAllowed("Cannot Trigger Transaction: Invalid Status")
        flow = PaymentRecordFlow(pr)
        try:
            transaction_id, payload = self.prepare_transaction(base_payload)
            response = self.perform_request(endpoint, "post", payload)
            if hasattr(response, "data") and response.data["Succeeded"]:
                status_code = response.status_code
                flow.store()
            else:
                status_code = HTTP_400_BAD_REQUEST
                flow.fail()
            response = Response(response.json(), status_code)
        except (PayloadMissingKeyError, ValueError, TypeError) as e:
            pr.message = e.args[0]
            response = Response(
                {"code": "validation_error", "message": e.args[0]},
                status=HTTP_400_BAD_REQUEST,
            )
            payload = response
        if response.status_code >= 300:
            flow.fail()
            pr.success = False
            response = Response(response.data, status=HTTP_400_BAD_REQUEST)
        else:
            pr.success = True
        pr.save()
        if update and response.status_code == 200:
            self.post_transaction(response, base_payload)
        return payload, response, endpoint

    def status(self, payload):
        """Query PalPay to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"/api/v1/moneytransfer/check-status/{transaction_id}"
        return None, self.perform_request(endpoint, "get"), endpoint

    def global_status(self, payload):
        """Query PalPay to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"{settings.PALPAY_HOST}/api/v1/moneytransfer/transactions/"
        payload = {}
        return (
            endpoint,
            payload,
            self.perform_request(endpoint, transaction_id, payload),
        )

    def post_transaction(self, response, payload):
        body = response.data
        record_code = payload["payment_record_code"]
        pr = PaymentRecord.objects.get(
            record_code=record_code,
            parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
        )

        pr.success = body["Succeeded"]
        pr.message = body["Message"]
        flow = PaymentRecordFlow(pr)
        if pr.success:
            pr.auth_code = body["Data"]["TransferId"]
            flow.store()
        else:
            pr.message += f" [{body['ErrorCode']}]"
            flow.fail()
        pr.fsp_data.update(body)
        pr.save()
