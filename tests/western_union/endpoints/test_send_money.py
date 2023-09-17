import pytest
import responses

from hope_payment_gateway.apps.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.western_union.exceptions import (
    InvalidChoiceFromCorridor,
    MissingValueInCorridor,
    PayloadIncompatible,
)
from hope_payment_gateway.apps.western_union.models import PaymentRecordLog
from tests.factories import CorridorFactory, PaymentRecordLogFactory


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
    PaymentRecordLogFactory(record_code=ref_no)
    assert PaymentRecordLog.objects.filter(record_code=ref_no).count() == 1
    send_money(hope_payload)
    assert PaymentRecordLog.objects.filter(record_code=ref_no).count() == 1


@responses.activate
def test_send_complete_corridor(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money.yaml")
    ref_no = "Y3snz233UkGt1Gw1"
    corridor_template = {
        "receiver": {
            "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
            "reason_for_sending": ["P012", "P014", "P015", "P016", "P017", "P018", "P019", "P020"],
        },
        "wallet_details": {"service_provider_code": "22901"},
    }
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
        # "corridor": "yes",
        "reason_for_sending": "P012",
    }
    CorridorFactory(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )
    PaymentRecordLogFactory(record_code=ref_no)
    assert PaymentRecordLog.objects.filter(record_code=ref_no).count() == 1
    send_money(hope_payload)
    pr = PaymentRecordLog.objects.get(record_code=ref_no)
    assert pr.success
    assert "mtcn" in pr.extra_data.keys()


@pytest.mark.parametrize(
    "corridor_template,exception",
    [
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                    "reason_for_sending": ["P012", "P014", "P015", "P016", "P017", "P018", "P019", "P020"],
                },
                "wallet_details": {"service_provider_code": 22901},
            },
            InvalidChoiceFromCorridor,
        ),
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                },
                "missing_value": {"service_provider_code": 22901},
            },
            PayloadIncompatible,
        ),
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": None}},
                },
            },
            MissingValueInCorridor,
        ),
    ],
)
def test_send_complete_corridor_ko(django_app, admin_user, corridor_template, exception):
    ref_no = "Y3snz233UkGt1Gw1"
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
        "corridor": "yes",
    }
    CorridorFactory(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )
    PaymentRecordLogFactory(record_code=ref_no)
    assert PaymentRecordLog.objects.filter(record_code=ref_no).count() == 1
    with pytest.raises(exception):
        send_money(hope_payload)
