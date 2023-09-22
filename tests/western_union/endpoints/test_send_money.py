import pytest
import responses

from hope_payment_gateway.apps.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.western_union.models import PaymentRecord

from ...factories import CorridorFactory, PaymentRecordFactory


# @_recorder.record(file_path="tests/western_union/endpoints/send_money_validation.yaml")
@responses.activate
def test_send_money_validation(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money_validation.yaml")
    hope_payload = {
        "record_uuid": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": "Y3snz233UkGt1Gw4",
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
    uuid = "681cbf43-a506-4bca-925c-cb10d89f6d92"
    hope_payload = {
        "record_uuid": uuid,
        "payment_record_code": "Y3snz233UkGt1Gw4",
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
    pr = PaymentRecordFactory(uuid=uuid)
    send_money(hope_payload)
    pr.refresh_from_db()
    assert pr.success
    assert pr.status == PaymentRecord.TRANSFERRED_TO_FSP
    assert PaymentRecord.objects.filter(uuid=uuid).count() == 1


@responses.activate
def test_send_complete_corridor(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money.yaml")
    uuid = "681cbf43-a506-4bca-925c-cb10d89f6d92"
    corridor_template = {
        "receiver": {
            "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
            "reason_for_sending": ["P012", "P014", "P015", "P016", "P017", "P018", "P019", "P020"],
        },
        "wallet_details": {"service_provider_code": "22901"},
    }
    hope_payload = {
        "record_uuid": uuid,
        "payment_record_code": "Y3snz233UkGt1Gw1",
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
        "corridor": "yes",
        "reason_for_sending": "P012",
    }
    CorridorFactory(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )
    pr = PaymentRecordFactory(uuid=uuid)
    send_money(hope_payload)
    pr.refresh_from_db()
    assert pr.success
    assert pr.status == PaymentRecord.TRANSFERRED_TO_FSP
    assert "mtcn" in pr.extra_data.keys()


def test_send_complete_corridor_no_exist(django_app, admin_user):
    # responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    # responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    # responses._add_from_file(file_path="tests/western_union/endpoints/send_money.yaml")
    uuid = "681cbf43-a506-4bca-925c-cb10d89f6d92"
    hope_payload = {
        "record_uuid": uuid,
        "payment_record_code": "Y3snz233UkGt1Gw1",
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
        "corridor": "yes",
        "reason_for_sending": "P012",
    }
    pr = PaymentRecordFactory(uuid=uuid)
    send_money(hope_payload)
    pr.refresh_from_db()
    assert not pr.success
    assert pr.status == PaymentRecord.ERROR
    assert pr.message == "Invalid corridor for ES/EUR"


@pytest.mark.parametrize(
    "corridor_template,message",
    [
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                    "reason_for_sending": ["P012", "P014", "P015", "P016", "P017", "P018", "P019", "P020"],
                },
                "wallet_details": {"service_provider_code": 22901},
            },
            "Invalid Choice reason_for_sending for AO12",
        ),
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                },
                "missing_value": {"service_provider_code": 22901},
            },
            "Wrong structure: missing_value should not be a leaf",
        ),
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": None}},
                },
            },
            "Missing Value in Corridor country_code",
        ),
    ],
)
def test_send_complete_corridor_ko(django_app, admin_user, corridor_template, message):
    uuid = "681cbf43-a506-4bca-925c-cb10d89f6d92"
    hope_payload = {
        "record_uuid": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": "Y3snz233UkGt1Gw1",
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
        "reason_for_sending": "AO12",
        "corridor": "yes",
    }
    CorridorFactory(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )
    pr = PaymentRecordFactory(uuid=uuid)
    send_money(hope_payload)
    pr.refresh_from_db()
    assert not pr.success
    assert pr.status == PaymentRecord.ERROR
    assert pr.message == message
