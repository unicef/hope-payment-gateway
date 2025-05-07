import pytest
from unittest.mock import patch
from constance.test import override_config
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import ServiceProviderCode, Corridor
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
        "template_code": "test",
    }


@pytest.fixture
def mock_corridor(mock_setup_data):
    return CorridorFactory(
        destination_country=mock_setup_data["destination_country"],
        destination_currency=mock_setup_data["destination_currency"],
        description="Test Corridor",
        template_code=mock_setup_data["template_code"],
    )


@pytest.fixture
def mock_response():
    return {
        "content": {},
        "content_response": {
            "MTML": {
                "REPLY": {
                    "DATA_CONTEXT": {
                        "RECORDSET": {
                            "GETDELIVERYOPTIONTEMPLATE": [
                                {
                                    "T_INDEX": "001",
                                    "DESCRIPTION": "wallet_details.service_provider_code;type;WALLET1;WP 1",
                                },
                                {
                                    "T_INDEX": "003",
                                    "DESCRIPTION": "other_field;type;VALUE;Description",
                                },
                            ]
                        }
                    }
                }
            }
        },
    }


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_option_template_success(wu_client, mock_response, wu, mock_setup_data, mock_corridor):
    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_option_template(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            mock_setup_data["template_code"],
        )

        mock_corridor.refresh_from_db()

        service_provider = ServiceProviderCode.objects.get(
            country=mock_setup_data["destination_country"],
            currency=mock_setup_data["destination_currency"],
        )

        assert response == mock_response
        assert mock_corridor.template is not None
        assert "wallet_details" in mock_corridor.template
        assert "service_provider_code" in mock_corridor.template["wallet_details"]
        assert mock_corridor.template["wallet_details"]["service_provider_code"] == "VALUE"
        assert service_provider.code == "VALUE"
        assert service_provider.description == "Description"


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_option_template_no_corridor(wu_client, mock_response, wu, mock_setup_data):
    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_option_template(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            mock_setup_data["template_code"],
        )

        assert response == mock_response
        assert not Corridor.objects.filter(
            destination_country=mock_setup_data["destination_country"],
            destination_currency=mock_setup_data["destination_currency"],
        ).exists()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_option_template_invalid_response(wu_client, wu, mock_setup_data, mock_corridor):
    invalid_response = {"content_response": {}}

    with patch.object(wu_client, "response_context", return_value=invalid_response):
        response = wu_client.das_delivery_option_template(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            mock_setup_data["template_code"],
        )

        mock_corridor.refresh_from_db()

        assert response == invalid_response
        assert not mock_corridor.template
        assert not ServiceProviderCode.objects.exists()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_delivery_option_template_existing_template(wu_client, mock_response, wu, mock_setup_data, mock_corridor):
    existing_template = {"existing": "template"}
    mock_corridor.template = existing_template
    mock_corridor.save()

    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_option_template(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            mock_setup_data["template_code"],
        )

        mock_corridor.refresh_from_db()

        assert response == mock_response
        assert mock_corridor.template == existing_template
