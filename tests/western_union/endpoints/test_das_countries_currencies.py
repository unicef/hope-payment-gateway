import pytest
from unittest.mock import patch
from constance.test import override_config


@pytest.fixture
def mock_setup_data():
    return {
        "destination_country": "US",
        "destination_currency": "USD",
        "identifier": "test_identifier",
        "counter_id": "test_counter",
    }


@pytest.fixture
def mock_response(mock_setup_data):
    return {
        "content": {},
        "content_response": {
            "MTML": {
                "REPLY": {
                    "DATA_CONTEXT": {
                        "HEADER": {"DATA_MORE": "N"},
                        "RECORDSET": {
                            "GETCOUNTRIESCURRENCIES": [
                                {
                                    "ISO_COUNTRY_CD": mock_setup_data["destination_country"],
                                    "CURRENCY_CD": mock_setup_data["destination_currency"],
                                    "COUNTRY_LONG": "United States",
                                    "CURRENCY_NAME": "US Dollar",
                                }
                            ]
                        },
                    }
                }
            }
        },
    }


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_countries_currencies_create_corridors_true(wu, wu_client, mock_response, mock_setup_data):
    with (
        patch.object(wu_client, "response_context", return_value=mock_response),
        patch.object(wu_client, "das_delivery_services") as mock_das_delivery_services,
    ):
        response = wu_client.das_countries_currencies(
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            create_corridors=True,
        )

        mock_das_delivery_services.assert_called_once_with(
            mock_setup_data["destination_country"],
            mock_setup_data["destination_currency"],
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            create_corridors=True,
        )
        assert response == mock_response


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_countries_currencies_create_corridors_false(wu, wu_client, mock_response, mock_setup_data):
    with (
        patch.object(wu_client, "response_context", return_value=mock_response),
        patch.object(wu_client, "das_delivery_services") as mock_das_delivery_services,
    ):
        response = wu_client.das_countries_currencies(
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
            create_corridors=False,
        )

        mock_das_delivery_services.assert_not_called()
        assert response == mock_response


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das_countries_currencies_response_no_dict(wu, wu_client, mock_setup_data):
    mock_response = {"content_response": None}
    with (
        patch.object(wu_client, "response_context", return_value=mock_response),
        patch.object(wu_client, "das_delivery_services") as mock_das_delivery_services,
    ):
        response = wu_client.das_countries_currencies(
            mock_setup_data["identifier"],
            mock_setup_data["counter_id"],
        )

        mock_das_delivery_services.assert_not_called()
        assert response == mock_response
