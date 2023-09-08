import responses

from hope_payment_gateway.apps.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.western_union.models import PaymentRecordLog


# @_recorder.record(file_path="tests/western_union/endpoints/send_money_validation.yaml")
@responses.activate
def test_send_money_validation(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money_validation.yaml")
    ref_no = "Y3snz233UkGt1Gw4"
    hope_payload = {
        "payment_record_code": ref_no,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "phone_no": "+94786661137",
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    payload = create_validation_payload(hope_payload)
    resp = send_money_validation(payload)
    assert (resp["title"], resp["code"]) == ("sendmoneyValidation", 200)


# @_recorder.record(file_path="tests/western_union/endpoints/send_money_complete.yaml")
@responses.activate
def test_send_complete(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money.yaml")
    ref_no = "Y3snz233UkGt1Gw4"
    hope_payload = {
        "payment_record_code": ref_no,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "phone_no": "+94786661137",
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    assert PaymentRecordLog.objects.filter(record_code=ref_no).count() == 0
    send_money(hope_payload)
    assert PaymentRecordLog.objects.get(record_code=ref_no)
