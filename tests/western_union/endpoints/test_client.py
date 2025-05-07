from unittest.mock import Mock

import pytest
import responses
from constance.test import override_config
from zeep.exceptions import TransportError
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient


def test_client_no_service():
    client = WesternUnionClient()
    resp = client.response_context(client.search_client, "WrongOne", dict)
    assert resp["title"] == "Service has no operation 'WrongOne'"
    assert resp["code"] == 500


def test_client_invalid():
    payload = {"i am": "invalid"}
    client = WesternUnionClient()
    resp = client.response_context(client.search_client, "Search", payload)

    assert resp["title"] == "Invalid Payload"
    assert resp["code"] == 400


def test_client_invalid_address():
    client = WesternUnionClient()
    resp = client.response_context(client.search_client, "Search", dict, wsdl_name="wrong_one", port="wrong_one")

    assert resp["title"] == "Service not found"
    assert resp["code"] == 400
    assert resp["error"] == "Service not found"


def test_client_transport_error():
    mock_client = Mock()
    mock_client.service.Search.side_effect = TransportError("Transport Error", status_code=400)
    client = WesternUnionClient()
    payload = {"i am": "valid"}
    resp = client.response_context(mock_client, "Search", payload)
    assert resp["title"] == "Transport Error [400]"
    assert resp["code"] == 400


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_client_error(wu):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_client_error.yaml")
    payload = {
        "payment_record_code": "asdasdas",
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
    payload = WesternUnionClient.create_validation_payload(payload)
    client = WesternUnionClient()
    resp = client.response_context(client.quote_client, "sendmoneyValidation", payload)

    assert resp["title"] == "business exception [xrsi:error-reply]"
    assert resp["code"] == 400
    assert resp["error"] == "E9256 SYSTEM ERROR - PLEASE RETRY"


@responses.activate
@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_client_non_std_error(wu):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_client_non_std_error.yaml")
    payload = {
        "payment_record_code": "asdasdas",
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
    payload = WesternUnionClient.create_validation_payload(payload)
    client = WesternUnionClient()
    resp = client.response_context(client.quote_client, "sendmoneyValidation", payload)
    assert resp["title"] == "business exception [xrsi:error-reply]"
    assert resp["code"] == 400
    assert resp["error"] == "generic error"
