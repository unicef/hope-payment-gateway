import base64
import json
import logging

from django.conf import settings

import requests
from urllib3.connectionpool import HTTPSConnectionPool

from hope_payment_gateway.apps.core.models import Singleton

logger = logging.getLogger(__name__)


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
        except HTTPSConnectionPool:
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

    def create_transaction(self, hope_payload):

        if self.token:

            url = settings.MONEYGRAM_HOST + "/disbursement/v1/transactions"

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

            headers = {
                "Content-Type": "application/json",
                "X-MG-ClientRequestId": hope_payload["payment_record_code"],
                "Authorization": "Bearer " + self.token,
            }

            payload = {
                "agentPartnerId": settings.MONEYGRAM_PARTNER_ID,
                "targetAudience": "AGENT_FACING",
                "userLanguage": "en-US",
                "destinationCountryCode": "USA",
                "destinationCountrySubdivisionCode": "US-MN",
                "serviceOptionCode": "WILL_CALL",
                "sendAmount": {"currencyCode": hope_payload["origination_currency"], "value": hope_payload["amount"]},
                "receiveCurrencyCode": hope_payload["destination_currency"],
                "initiator": {"method": "batch", "userId": "abc", "userType": "consumer"},
                "autoCommit": True,
                "receiver": {
                    "name": {
                        "firstName": hope_payload["first_name"],
                        "middleName": hope_payload.get("middle_name", ""),
                        "lastName": hope_payload["last_name"],
                        "secondLastName": "",
                    }
                },
            }
            response = self.perform_request(url, headers, payload)
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
            response = None

        return response
