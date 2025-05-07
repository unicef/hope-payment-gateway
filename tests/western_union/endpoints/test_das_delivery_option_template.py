import pytest
from unittest.mock import patch
from constance.test import override_config
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import ServiceProviderCode
from tests.factories import CorridorFactory


@pytest.fixture
def wu_client():
    return WesternUnionClient()


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
                                    "T_INDEX": "002",
                                    "DESCRIPTION": "wallet_details.service_provider_code;type;WALLET2;WP 2",
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
def test_das_delivery_option_template_success(wu_client, mock_response, wu):
    destination_country = "US"
    destination_currency = "USD"
    identifier = "test_identifier"
    counter_id = "test_counter"
    template_code = "test"

    corridor = CorridorFactory(
        destination_country=destination_country,
        destination_currency=destination_currency,
        description="Test Corridor",
        template_code=template_code,
    )
    with patch.object(wu_client, "response_context", return_value=mock_response):
        response = wu_client.das_delivery_option_template(
            destination_country,
            destination_currency,
            identifier,
            counter_id,
            template_code,
        )

        corridor.refresh_from_db()

        service_provider = ServiceProviderCode.objects.get(
            country=destination_country,
            currency=destination_currency,
        )

        assert response == mock_response
        assert corridor.template is not None
        assert "wallet_details" in corridor.template
        assert "service_provider_code" in corridor.template["wallet_details"]
        assert corridor.template["wallet_details"]["service_provider_code"] == "VALUE"
        assert service_provider.code == "VALUE"
        assert service_provider.description == "Description"
