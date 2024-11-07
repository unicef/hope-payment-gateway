import base64
import json
import logging

from django.conf import settings

import phonenumbers
import requests
from phonenumbers import NumberParseException
from urllib3.exceptions import PoolError

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


MONEYGRAM_DM_MAPPING = {
    "WILL_CALL": "WILL_CALL",
    "DIRECT_TO_ACCT": "DIRECT_TO_ACCT",
    "BANK_DEPOSIT": "DIRECT_TO_ACCT",
}


class PayloadMissingKey(Exception):
    pass


class MoneyGramClient(metaclass=Singleton):
    token = ""
    expires_in = None
    token_response = None

    def __init__(self):
        self.get_token()

    def get_token(self):
        url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
        credentials = f"{settings.MONEYGRAM_CLIENT_ID}:{settings.MONEYGRAM_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": "Basic " + encoded_credentials}

        try:
            response = requests.get(url, headers=headers)
        except PoolError:
            self.token = None
            self.token_response = None
        else:
            if response.status_code == 200:
                parsed_response = json.loads(response.text)
                self.token = parsed_response["access_token"]
                self.expires_in = parsed_response["expires_in"]
            else:
                logger.warning("Invalid token")
                self.token = None
                self.token_response = response

    def prepare_transaction(self, payload):

        raw_phone_no = payload.get("phone_no", "N/A")
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
            if not (key in payload.keys() and payload[key]):
                raise PayloadMissingKey("InvalidPayload: {} is missing in the payload".format(key))

        return {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
            "userLanguage": "en-US",
            "destinationCountryCode": payload["destination_country"],
            # "destinationCountrySubdivisionCode": "US-NY",
            "receiveCurrencyCode": payload["destination_currency"],
            "serviceOptionCode": payload.get("delivery_services_code", "WILL_CALL"),
            # "serviceOptionRoutingCode": "74261037",  # TODO
            "autoCommit": "true",
            "sendAmount": {"currencyCode": payload["origination_currency"], "value": payload["amount"]},
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
                        "firstName": payload["first_name"],
                        "middleName": payload.get("middle_name", ""),
                        "lastName": payload["last_name"],
                    },
                    "address": {
                        "line1": payload.get("address", "Via di Acilia"),
                        "city": payload.get("city", "Roma"),
                        "countryCode": payload["destination_country"],
                        "postalCode": 55442,
                    },
                    "mobilePhone": {"number": phone_number, "countryDialCode": country_code},
                }
            },
        }

    def create_transaction(self, payload):

        if self.token:

            url = settings.MONEYGRAM_HOST + "/disbursement/v1/transactions"
            enriched_payload = self.prepare_transaction(payload)
            headers = {
                "Content-Type": "application/json",
                "X-MG-ClientRequestId": enriched_payload["payment_record_code"],
                "Authorization": "Bearer " + self.token,
            }

            response = self.perform_request(url, headers, payload)
            self.transaction_callback(enriched_payload, response.json())
            return response

        else:
            return self.token_response

    def perform_request(self, url, headers, payload=None):
        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                parsed_response = json.dumps(json.loads(response.text), indent=2)
                print(parsed_response)
            else:
                print("Request failed with status code:", response.status_code)
                print(json.dumps(json.loads(response.text), indent=2))

        except (requests.exceptions.RequestException, requests.exceptions.MissingSchema) as e:
            print("An error occurred:", e)
            response = dict

        return response

    def transaction_callback(self, payload, response):
        record_code = payload["payment_record_code"]
        pr = PaymentRecord.objects.get(record_code=record_code)
        pr.fsp_code = response["referenceNumber"]
        pr.success = True
        pr.payout_amount = response["receiveAmount"]["amount"]["value"]
        pr.extra_data.update(
            {
                "fee": response["receiveAmount"]["fees"]["value"],
                "fee_currency": response["receiveAmount"]["fees"]["currencyCode"],
                "taxes": response["receiveAmount"]["taxes"]["value"],
                "taxes_currency": response["receiveAmount"]["taxes"]["currencyCode"],
                "expectedPayoutDate": response["expectedPayoutDate"],
                "transactionId": response["transactionId"],
            }
        )
        flow = PaymentRecordFlow(pr)
        flow.store()
