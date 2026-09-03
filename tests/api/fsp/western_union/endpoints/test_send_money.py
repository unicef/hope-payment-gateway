from unittest.mock import patch

import pytest
import responses
from constance.test import override_config
from factories import CorridorFactory, PaymentRecordFactory

from hope_payment_gateway.api.western_union.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.exceptions import (
    InvalidCorridorError,
    InvalidChoiceFromCorridorError,
    PayloadIncompatibleError,
)
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentRecordState


# @_recorder.record(file_path="tests/api/fsp/western_union/endpoints/send_money_validation.yaml")
@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_money_validation(django_app, admin_user, wu, wu_client):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/send_money_validation.yaml")
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": "Y3snz233UkGt1Gw4",
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    payload = WesternUnionClient().create_validation_payload(payload)
    resp = wu_client.send_money_validation(payload)
    assert (resp["title"], resp["code"]) == ("sendmoneyValidation", 200)


@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_money_validation_ko(django_app, admin_user, wu, wu_client):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/send_money_validation_ko.yaml")
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": "681cbf43",
        "first_name": "Aldo",
        "last_name": "Baglio",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 1200,
        "delivery_services_code": "000",
    }
    payload = WesternUnionClient().create_validation_payload(payload)
    resp = wu_client.send_money_validation(payload)
    assert (resp["title"], resp["code"]) == (
        "business exception [xrsi:error-reply]",
        400,
    )


# @_recorder.record(file_path="tests/api/fsp/western_union/endpoints/send_money_complete.yaml")
@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete(django_app, admin_user, wu, wu_client, payment_record_send_complete):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/send_money.yaml")
    record_code = "Y3snz233UkGt1Gw4"
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    pr = payment_record_send_complete
    wu_client.create_transaction(payload)
    pr.refresh_from_db()
    assert pr.success
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP
    assert PaymentRecord.objects.filter(record_code=record_code).count() == 1


@pytest.fixture
def payment_record_send_complete(wu):
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw4", parent__fsp=wu)


@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete_corridor(
    django_app, admin_user, wu, wu_client, payment_record_send_complete_corridor, corridor_send_complete_corridor
):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/send_money.yaml")
    record_code = "Y3snz233UkGt1Gw1"
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_mechanism": "mobile_money",
        "account": {
            "number": "+94786661137",
        },
        "delivery_services_code": "800",
        "reason_for_sending": "P012",
    }
    pr = payment_record_send_complete_corridor
    wu_client.create_transaction(payload)
    pr.refresh_from_db()
    assert pr.success
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP
    assert "mtcn" in pr.fsp_data


@pytest.fixture
def corridor_send_complete_corridor():
    corridor_template = {
        "receiver": {
            "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
            "reason_for_sending": [
                "P012",
                "P014",
                "P015",
                "P016",
                "P017",
                "P018",
                "P019",
                "P020",
            ],
        },
        "wallet_details": {"service_provider_code": "22901"},
    }
    return CorridorFactory.create(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )


@pytest.fixture
def payment_record_send_complete_corridor(wu):
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw1", parent__fsp=wu)


@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete_corridor_no_exist(
    django_app, admin_user, wu, wu_client, payment_record_send_complete_corridor_no_exist
):
    record_code = "Y3snz233UkGt1Gw1"
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_mechanism": "mobile_money",
        "delivery_services_code": "800",
        "reason_for_sending": "P012",
        "account": {
            "number": "+94786661137",
        },
    }
    pr = payment_record_send_complete_corridor_no_exist
    with pytest.raises(InvalidCorridorError):
        wu_client.create_transaction(payload)
    pr.refresh_from_db()
    assert not pr.success
    assert pr.status == PaymentRecordState.ERROR
    assert pr.message == "Invalid corridor for ES/EUR"


@pytest.fixture
def payment_record_send_complete_corridor_no_exist(wu):
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw1", parent__fsp=wu)


@pytest.fixture
def payment_record_for_corridor_ko(corridor_template, wu):
    CorridorFactory.create(
        destination_country="ES",
        destination_currency="EUR",
        template=corridor_template,
    )
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw4", parent__fsp=wu)


@pytest.mark.parametrize(
    ("corridor_template", "message", "exc_class"),
    [
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                    "reason_for_sending": [
                        "P012",
                        "P014",
                        "P015",
                        "P016",
                        "P017",
                        "P018",
                        "P019",
                        "P020",
                    ],
                },
                "wallet_details": {"service_provider_code": 22901},
            },
            "Invalid Choice reason_for_sending for AO12",
            InvalidChoiceFromCorridorError,
        ),
        (
            {
                "receiver": {
                    "mobile_phone": {"phone_number": {"country_code": 229, "national_number": None}},
                },
                "missing_value": {"service_provider_code": 22901},
            },
            "Wrong structure: missing_value should not be a leaf",
            PayloadIncompatibleError,
        ),
    ],
)
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete_corridor_ko(
    django_app,
    admin_user,
    corridor_template,
    message,
    wu,
    exc_class,
    wu_client,
    payment_record_for_corridor_ko,
):
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": payment_record_for_corridor_ko.record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_mechanism": "mobile_money",
        "delivery_services_code": "800",
        "reason_for_sending": "AO12",
    }
    pr = payment_record_for_corridor_ko
    with pytest.raises(exc_class):
        wu_client.create_transaction(payload)
    pr.refresh_from_db()
    assert not pr.success
    assert pr.status == PaymentRecordState.ERROR
    assert pr.message == message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete_send_money_validation_response_error(wu, wu_client, payment_record_validation_response_error):
    record_code = "Y3snz233UkGt1Gw4"
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    pr = payment_record_validation_response_error

    mock_response = {
        "code": 400,
        "error": "Error",
    }
    with patch.object(wu_client, "send_money_validation", return_value=mock_response):
        response = wu_client.create_transaction(payload)
        pr.refresh_from_db()
        assert pr.message == f"Send Money Validation failed: {mock_response['error']}"
        assert pr.status == PaymentRecordState.ERROR
        assert pr.success is False
        assert response == mock_response


@pytest.fixture
def payment_record_validation_response_error(wu):
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw4", parent__fsp=wu)


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_send_complete_send_money_store_response_error(wu, wu_client, payment_record_store_response_error):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/send_money_validation.yaml")

    record_code = "Y3snz233UkGt1Gw4"
    payload = {
        "remote_id": "681cbf43-a506-4bca-925c-cb10d89f6d92",
        "payment_record_code": record_code,
        "first_name": "Aliyah",
        "last_name": "GRAY",
        "account": {
            "number": "+94786661137",
        },
        "source_country": "US",
        "source_currency": "USD",
        "transaction_type": "WMF",
        "destination_country": "ES",
        "destination_currency": "EUR",
        "duplication_enabled": "D",
        "amount": 199900,
        "delivery_services_code": "000",
    }
    pr = payment_record_store_response_error

    mock_response = {
        "code": 400,
        "error": "Error",
    }
    with patch.object(wu_client, "send_money_store", return_value=mock_response):
        response = wu_client.create_transaction(payload)
        pr.refresh_from_db()
        assert pr.message == f"Send Money Store: {mock_response['error']}"
        assert pr.status == PaymentRecordState.ERROR
        assert pr.success is False
        assert response == mock_response


@pytest.fixture
def payment_record_store_response_error(wu):
    return PaymentRecordFactory.create(record_code="Y3snz233UkGt1Gw4", parent__fsp=wu)
