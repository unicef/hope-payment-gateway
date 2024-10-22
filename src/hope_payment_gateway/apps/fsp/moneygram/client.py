import base64
import json
import logging

from django.conf import settings

import phonenumbers
import requests
from phonenumbers import NumberParseException
from requests.exceptions import ConnectionError
from rest_framework.response import Response

from hope_payment_gateway.apps.core.models import Singleton

logger = logging.getLogger(__name__)


MONEYGRAM_DM_MAPPING = {
    "WILL_CALL": "WILL_CALL",
    "DIRECT_TO_ACCT": "DIRECT_TO_ACCT",
    "BANK_DEPOSIT": "DIRECT_TO_ACCT",
    "WILLCALL_TO": "WILLCALL_TO",
    "2_HOUR": "2_HOUR",
    "OVERNIGHT": "OVERNIGHT",
    "OVERNIGHT2ANY": "OVERNIGHT2ANY",
    "24_HOUR": "24_HOUR",
    "CARD_DEPOSIT": "CARD_DEPOSIT",
    "HOME_DELIVERY": "HOME_DELIVERY",
}


class PayloadMissingKey(Exception):
    pass


class InvalidToken(Exception):
    pass


class MoneyGramClient(metaclass=Singleton):
    token = ""
    expires_in = None

    def __init__(self):
        self.set_token()

    def set_token(self):
        url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
        credentials = f"{settings.MONEYGRAM_CLIENT_ID}:{settings.MONEYGRAM_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": "Basic " + encoded_credentials}

        try:
            response = requests.get(url, headers=headers)
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
        return {
            "Content-Type": "application/json",
            "X-MG-ClientRequestId": request_id,
            "content-type": "application/json",
            "Authorization": "Bearer " + self.token,
        }

    @staticmethod
    def get_basic_payload():
        return {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
            "userLanguage": "en-US",
        }

    def prepare_transaction(self, hope_payload):
        raw_phone_no = hope_payload.get("phone_no", "N/A")
        try:
            phone_no = phonenumbers.parse(raw_phone_no, None)
            phone_number = phone_no.national_number
            country_code = phone_no.country_code
        except NumberParseException:
            phone_number = raw_phone_no
            country_code = None

        for key in [
            "first_name",
            "last_name",
            "amount",
            "destination_country",
            "destination_currency",
            "payment_record_code",
        ]:
            if not (key in hope_payload.keys() and hope_payload[key]):
                raise PayloadMissingKey("InvalidPayload: {} is missing in the payload".format(key))
        transaction_id = hope_payload["payment_record_code"]
        payload = {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
            "userLanguage": "en-US",
            "destinationCountryCode": hope_payload["destination_country"],
            # "destinationCountrySubdivisionCode": "US-NY",
            "receiveCurrencyCode": hope_payload["destination_currency"],
            "serviceOptionCode": hope_payload.get("delivery_services_code", "WILL_CALL"),
            # "serviceOptionRoutingCode": "74261037",  # TODO
            "autoCommit": "true",
            "sendAmount": {"currencyCode": hope_payload["origination_currency"], "value": hope_payload["amount"]},
            "sender": {
                "business": {
                    "businessName": "UNICEF",
                    "legalEntityName": "UNICEF",
                    "businessType": "ACCOMMODATION_HOTELS",
                    "businessRegistrationNumber": settings.MONEYGRAM_REGISTRATION_NUMBER,
                    "businessIssueDate": "2024-04-29",
                    "businessCountryOfRegistration": "USA",
                    "address": {
                        "line1": "3 United Nations Plaza",
                        "city": "NEW YORK",
                        "countrySubdivisionCode": "US-NY",
                        "countryCode": "USA",
                        "postalCode": 10017,
                    },
                    "contactDetails": {"phone": {"number": 2123267000, "countryDialCode": 1}},
                }
            },
            "beneficiary": {
                "consumer": {
                    "name": {
                        "firstName": hope_payload["first_name"],
                        "middleName": hope_payload.get("middle_name", ""),
                        "lastName": hope_payload["last_name"],
                    },
                    "address": {
                        "line1": hope_payload.get("address", "Via di Acilia"),
                        "city": hope_payload.get("city", "Roma"),
                        "countryCode": hope_payload["destination_country"],
                        "postalCode": 55442,
                    },
                    "mobilePhone": {"number": phone_number, "countryDialCode": country_code},
                }
            },
        }
        return transaction_id, payload

    def create_transaction(self, hope_payload):

        endpoint = "/disbursement/v1/transactions"
        transaction_id, payload = self.prepare_transaction(hope_payload)
        return self.perform_request(endpoint, transaction_id, payload)

    def prepare_quote(self, hope_payload: dict):

        transaction_id = hope_payload["payment_record_code"]
        payload = self.get_basic_payload()
        payload.update(
            {
                "destinationCountryCode": hope_payload["destination_country"],
                "serviceOptionCode": hope_payload.get("delivery_services_code", None),
                "beneficiaryTypeCode": "Consumer",
                "sendAmount": {"currencyCode": hope_payload["origination_currency"], "value": hope_payload["amount"]},
            }
        )
        return transaction_id, payload

    def quote(self, hope_payload):

        endpoint = "/disbursement/v1/transactions/quote"
        transaction_id, payload = self.prepare_quote(hope_payload)
        return self.perform_request(endpoint, transaction_id, payload)

    def perform_request(self, endpoint, transaction_id, payload):
        url = settings.MONEYGRAM_HOST + endpoint
        headers = self.get_headers(transaction_id)
        for _ in range(2):
            try:
                response = requests.post(url, json=payload, headers=headers)
                response = Response(response.json(), response.status_code)
                break
            except (requests.exceptions.RequestException, requests.exceptions.MissingSchema) as e:
                print("An error occurred:", e)
                response = dict
                break
            except Exception as e:
                print("Token Expired:", e)
                self.set_token()

        if response.status_code == 200:
            parsed_response = response.data
            print(parsed_response)
        else:
            print("Request failed with status code:", response.status_code)
            print(response.data)
        return response
