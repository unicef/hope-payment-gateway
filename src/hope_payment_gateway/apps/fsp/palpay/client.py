import hashlib
import hmac
import logging
import uuid

import requests
from constance import config
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.utils import get_phone_number
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord, FinancialServiceProvider
from hope_payment_gateway.config import settings
import time

logger = logging.getLogger(__name__)


class PayloadMissingKeyError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


def get_hmac_sha512(data: str, key: str) -> str:
    hmac_hash = hmac.new(key.encode("utf-8"), data.encode("utf-8"), hashlib.sha512)
    return hmac_hash.hexdigest().lower()


class PalPayClient(FSPClient, metaclass=Singleton):
    def get_headers(self):
        client_id = settings.PALPAY_CLIENT_ID
        client_secret = settings.PALPAY_CLIENT_SECRET
        url = f"{settings.PALPAY_HOST}api/v1/moneytransfer/transfer/120"
        request_method = "POST"

        unix_timestamp = str(time.time())
        transaction_id = uuid.uuid4().hex

        concatenated_string = client_id + request_method + url + unix_timestamp + transaction_id

        hmac_signature = get_hmac_sha512(concatenated_string, client_secret)
        return {
            "Authorization": f"{client_id}:{hmac_signature}:{transaction_id}:{unix_timestamp}",
            "Content-Type": "application/json",
        }

    def get_profile(self):
        url = f"{settings.PALPAY_HOST}/api/v1/moneytransfer/profile"
        response = requests.get(url, headers=self.get_headers(), timeout=30)
        breakpoint()
        return None, response.json()

    def prepare_transaction(self, base_payload):
        """Prepare the payload to create transactions."""
        raw_phone_no = base_payload.get("phone_no", "N/A")
        phone_number, country_code = get_phone_number(raw_phone_no)
        transaction_id = base_payload["payment_record_code"]

        fsp = FinancialServiceProvider.objects.get(vendor_number=config.PALPAY_VENDOR_NUMBER)
        if not fsp.configuration:
            _, fsp.configuration = self.get_profile()
            fsp.save()
        configuration = fsp.configuration

        full_name = " ".join(
            [
                base_payload[value]
                for value in ["first_name", "middle_name", "last_name", "second_last_name"]
                if base_payload.get(value)
            ]
        )
        try:
            payload = {
                "profileId": configuration.get("profile_id"),
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
        reference_number = "transRefNo"
        endpoint = f"/api/v1/moneytransfer/transfer/{reference_number}"

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
            flow.fail()
            pr.success = False
            response = Response(response.data, status=HTTP_400_BAD_REQUEST)
        else:
            pr.success = True
        pr.save()
        if update and response.status_code == 200:
            self.post_transaction(response, base_payload)

        return endpoint, payload, response

    def status(self, payload):
        """Query PalPay to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"/api/v1/moneytransfer/check-status/{transaction_id}"
        payload = {}
        return endpoint, payload, self.perform_request(endpoint, transaction_id, payload)

    def global_status(self, payload):
        """Query PalPay to get information regarding the transaction status."""
        record = PaymentRecord.objects.get(record_code=payload["payment_record_code"])
        transaction_id = record.fsp_code
        endpoint = f"{settings.PALPAY_HOST}/api/v1/moneytransfer/transactions/"
        payload = {}
        return endpoint, payload, self.perform_request(endpoint, transaction_id, payload)
