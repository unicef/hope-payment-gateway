from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.utils import MONEY_IN_TIME, WALLET, WMF, snapshot_example


def get_send_money_validation_payload(pk, wallet_no=None):
    print("Send Money Validation: Creating Payload")
    obj = PaymentRecord.objects.get(pk=pk)

    if obj.status != PaymentRecord.STATUS_PENDING:
        raise Exception("The Payment Record is not in status Pending")
    if hasattr(obj, "household_snapshot"):
        snapshot_data = obj.household_snapshot
    else:
        # raise MissingHousehold
        snapshot_data = snapshot_example

    collector = snapshot_data["primary_collector"]

    # if wallet:
    #     print("Amending Payload")
    #     corridor = Corridor.objects.get(id=wallet)
    #     payload = integrate_payload(payload, corridor.template)
    #     print(payload)

    return {
        "payment_record_code": obj.unicef_id,
        "first_name": collector["given_name"],
        "last_name": collector["family_name"],
        "phone_no": collector["phone_no"],
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": WMF,
        "destination_country": "ES",  # core countrycodemap
        "destination_currency": "EUR",  # obj.currency
        "duplication_enabled": "D",
        "amount": int(obj.entitlement_quantity * 100),
        "delivery_services_code": WALLET if wallet_no else MONEY_IN_TIME,
    }
