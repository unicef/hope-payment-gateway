from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import sender, unicef, usd, web, WMF, MONEY_IN_TIME, \
    snapshot_example


def send_money_store(pk, payload=None):
    if payload is None:
        print("Send Money Validation: Creating Payload")
        obj = PaymentRecord.objects.get(pk=pk)
        if obj.status != PaymentRecord.STATUS_PENDING:
            return {"title": "The Payment Record is not in status Pending", "code": 400}
        if hasattr(obj, 'household_snapshot'):
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

        mtcn = "7070587695"
        new_mtcn = "2324387070587695"
        instant_code = "010300002010030100103MSG02010030101103FEE1204300013043000961501010020100301099200101C0211UDI0000009299210417wufxspd0002046230"

        receiver = {
            "name": {"first_name": first_name, "last_name": last_name, "name_type": "D"},
            "email": email,
        }

        financials = {
            'originators_principal_amount': 254455,
            'destination_principal_amount': 199900,
            'third_party_amount': None,
            'principal_USD': None,
            'gross_total_amount': 257455,
            'plus_charges_amount': 0,
            'pay_amount': None,
            'principal_dollar_amount': None,
            'principal_amount': None,
            'surcharge': None,
            'charges': 3000,
            'tolls': None,
            'promo_discount_amount': None,
            'originating_currency_principal': None,
            'principal_in_words': None,
            'canadian_dollar_exchange_fee': None,
            'message_charge': 0,
            'incr_message_charge': None,
            'aggregated_amount': None,
            'available_amount': None,
            'sum_charges': None,
            'exchange_fee': None,
            'conversion_fee': None,
            'second_exchange_fee': None,
            'money_transfer_limit': None,
            'transaction_limit': None,
            'daily_limit': None,
            'cumulative_total_for_day': None,
            'addl_services_fees': None,
            'add_principal': None,
            'speed_of_delivery': [],
            'total_undiscounted_charges': None,
            'total_discount': None,
            'total_discounted_charges': None,
            'min_transaction_limit': None,
            'max_transaction_limit': None
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
        }

        instant_notification = {
            "addl_service_charges": instant_code,
        }

        delivery_services = {"code": delivery_services_code}

        payload = {
            "device": web,
            "channel": unicef,
            "instant_notification": instant_notification,
            "sender": sender,
            "receiver": receiver,
            "payment_details": payment_details,
            "financials": financials,
            "foreign_remote_system": usd,
            "delivery_services": delivery_services,
            "mtcn": mtcn,
            "new_mtcn": new_mtcn,
        }
    else:
        print("Send Money Store: Passed Payload")

    client = WesternUnionClient("SendMoneyStore_Service_H2HService.wsdl")
    response = client.response_context("SendMoneyStore_H2H", payload)
    return response
