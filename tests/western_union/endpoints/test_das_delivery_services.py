import pytest
from unittest.mock import patch
from constance.test import override_config

from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from tests.factories import CorridorFactory


@pytest.fixture
def wu_client():
    return WesternUnionClient()


@pytest.fixture
def mock_setup_data():
    return {
        "destination_country": "US",
        "destination_currency": "USD",
        "identifier": "test_identifier",
        "counter_id": "test_counter",
    }


@pytest.fixture
def mock_response():
    return {
        "content": {},
        "content_response": {
            "MTML": {
                "REPLY": {
                    "DATA_CONTEXT": {
                        "RECORDSET": {
                            "GETDELIVERYSERVICES": [
                                {
                                    "SVC_CODE": "800",
                                    "TEMPLT": "CODE",
                                    "SVC_DESC": "Test Service",
                                }
                            ]
                        }
                    }
                }
            }
        },
    }


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_services_create_corridors_true(wu_client, wu, mock_response, mock_setup_data):
    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_services(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            create_corridors=True,
        )
        corridor = Corridor.objects.get(
            destination_country=mock_setup_data["destination_country"],
            destination_currency=mock_setup_data["destination_currency"],
            description=f"{mock_setup_data['destination_country']}: {mock_setup_data['destination_currency']}",
            template_code="CODE",
        )
        assert response == mock_response
        assert corridor.template_code == "CODE"
        assert (
            corridor.description
            == f"{mock_setup_data['destination_country']}: {mock_setup_data['destination_currency']}"
        )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_services_no_wallet_service(wu_client, wu, mock_setup_data):
    mock_response = {
        "content_response": {
            "MTML": {
                "REPLY": {
                    "DATA_CONTEXT": {
                        "RECORDSET": {
                            "GETDELIVERYSERVICES": [
                                {
                                    "SVC_CODE": "900",
                                    "TEMPLT": "TEST_TEMPLATE",
                                    "SVC_DESC": "Test Service",
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_services(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
        )

        assert response == mock_response
        assert not Corridor.objects.filter(
            destination_country=mock_setup_data["destination_country"],
            destination_currency=mock_setup_data["destination_currency"],
        ).exists()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_services_invalid_response(wu_client, wu, mock_setup_data):
    invalid_response = {"content_response": {}}

    with patch.object(wu_client, "response_context", return_value=invalid_response):
        response = wu_client.das_delivery_services(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
        )

        assert response == invalid_response
        assert not Corridor.objects.filter(
            destination_country=mock_setup_data["destination_country"],
            destination_currency=mock_setup_data["destination_currency"],
        ).exists()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_services_existing_corridor(wu_client, mock_response, wu, mock_setup_data):
    existing_corridor = CorridorFactory(
        destination_country=mock_setup_data["destination_country"],
        destination_currency=mock_setup_data["destination_currency"],
        description="Existing Corridor",
        template_code="CODE",
    )

    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_services(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            create_corridors=False,
        )

        existing_corridor.refresh_from_db()

        assert response == mock_response
        assert existing_corridor.template_code == "CODE"
        assert existing_corridor.description == "Existing Corridor"
