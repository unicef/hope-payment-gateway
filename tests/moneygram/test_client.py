from django.test import override_settings

import pytest
import responses

from hope_payment_gateway.apps.fsp.moneygram.client import MoneyGramClient

# from responses import _recorder
# @_recorder.record(file_path="tests/moneygram/responses/token.yaml")


@responses.activate
@override_settings(MONEYGRAM_HOST="https://sandboxapi.moneygram.com")
def test_get_token():
    # responses.get("https://sandboxapi.moneygram.com/oauth/accesstoken?grant_type=client_credentials")
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()

    assert client.token == "HMfWVGb6AYGmx3B07JSXsfIZQw6Z"
    assert client.expires_in == "3599"


# @_recorder.record(file_path="tests/moneygram/responses/transaction.yaml")
@responses.activate
@pytest.mark.django_db
@pytest.mark.skip
@override_settings(MONEYGRAM_HOST="https://sandboxapi.moneygram.com")
def test_create_transaction():
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/transaction.yaml")
    client = MoneyGramClient()

    payload = {
        "first_name": "Alice",
        "last_name": "Foo",
        "amount": 1000,
        "origination_currency": "IT",
        "destination_country": "AF",
        "destination_currency": "USD",
        "payment_record_code": "code-123",
    }

    response = client.create_transaction(payload)

    assert response.status_code == 401
