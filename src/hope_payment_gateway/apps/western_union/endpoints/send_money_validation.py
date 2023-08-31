from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import (
    MONEY_IN_TIME,
    WMF,
    sender,
    snapshot_example,
    unicef,
    usd,
    web,
)


def send_money_validation(pk, payload=None):
    # for cash just name
    # for wallet delivery option template

    if payload is None:
        print("Send Money Validation: Creating Payload")
        obj = PaymentRecord.objects.get(pk=pk)
        if obj.status != PaymentRecord.STATUS_PENDING:
            return {"title": "The Payment Record is not in status Pending", "code": 400}
        if hasattr(obj, "household_snapshot"):
            snapshot_data = obj.household_snapshot
        else:
            # raise MissingHousehold
            snapshot_data = snapshot_example

        collector = snapshot_data["primary_collector"]
        first_name = collector["given_name"]
        last_name = collector["family_name"]
        email = "john@smith.com"  # ????
        phone_no = collector["phone_no"]
        source_country = "US"
        source_currency = "USD"
        transaction_type = WMF
        destination_country = "ES"  # core countrycodemap
        destination_currency = "EUR"  # obj.currency
        duplication_enabled = "D"
        amount = int(obj.entitlement_quantity * 100)
        delivery_services_code = MONEY_IN_TIME

        receiver = {
            "name": {"first_name": first_name, "last_name": last_name, "name_type": "D"},
            "email": email,
        }
        financials = {
            # "originators_principal_amount": amount,
            "destination_principal_amount": amount,
        }
        payment_details = {
            "recording_country_currency": {  # sending country
                "iso_code": {
                    "country_code": "US",
                    "currency_code": "USD",
                },
            },
            "destination_country_currency": {  # destination
                "iso_code": {
                    "country_code": destination_country,
                    "currency_code": destination_currency,
                },
            },
            "originating_country_currency": {  # sending country
                "iso_code": {
                    "country_code": source_country,
                    "currency_code": source_currency,
                },
            },
            "transaction_type": transaction_type,
            "payment_type": "Cash",
            "duplicate_detection_flag": duplication_enabled,
            # needed for US and MEX
            # "expected_payout_location": {
            #     "state_code": "NY",
            #     "city": "New York"
            # }
        }

        delivery_services = {"code": delivery_services_code}

        payload = {
            "device": web,
            "channel": unicef,
            "sender": sender,
            "receiver": receiver,
            "payment_details": payment_details,
            "financials": financials,
            "delivery_services": delivery_services,
            "foreign_remote_system": usd,
        }
    else:
        print("Send Money Validation: Passed Payload")
    client = WesternUnionClient("SendMoneyValidation_Service_H2HService.wsdl")
    return client.response_context("sendmoneyValidation", payload)
