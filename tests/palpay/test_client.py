import pytest
import responses
from constance.test import override_config
from factories import PaymentRecordFactory
from responses import _recorder  # noqa

from hope_payment_gateway.apps.fsp.palpay import DELIVERED, RECEIVED, REFUNDED, SENT
from hope_payment_gateway.apps.fsp.palpay.client import InvalidTokenError, PalPayClient, update_status
from hope_payment_gateway.apps.gateway.models import PaymentRecordState

# @_recorder.record(file_path="tests/palpay/responses/token.yaml")


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_get_token_ko(mg):
    responses._add_from_file(file_path="tests/palpay/responses/token_ko.yaml")
    with pytest.raises(InvalidTokenError):
        PalPayClient()


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_get_token(mg):
    responses._add_from_file(file_path="tests/palpay/responses/token.yaml")
    client = PalPayClient()
    assert client.token == "HMfWVGb6AYGmx3B07JSXsfIZQw6Z"
    assert client.expires_in == "3599"


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_get_headers_token():
    responses._add_from_file(file_path="tests/palpay/responses/token.yaml")
    client = PalPayClient()
    assert client.get_headers("request_id") == {
        "Content-Type": "application/json",
        "X-MG-ClientRequestId": "request_id",
        "content-type": "application/json",
        "Authorization": "Bearer HMfWVGb6AYGmx3B07JSXsfIZQw6Z",
    }


@pytest.mark.django_db
@responses.activate
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_get_basic_payload():
    responses._add_from_file(file_path="tests/palpay/responses/token.yaml")
    client = PalPayClient()
    assert client.get_basic_payload(agent_partner_id="AAAAAA") == {
        "targetAudience": "AGENT_FACING",
        "agentPartnerId": "AAAAAA",
        "userLanguage": "en-US",
    }


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_prepare_transactions(mg):
    client = PalPayClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        "first_name": "Alen",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    assert client.prepare_transaction(pr.get_payload()) == (
        pr_code,
        {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": "AAAAAA",
            "userLanguage": "en-US",
            "destinationCountryCode": "IT",
            "sendCurrencyCode": "USD",
            "serviceOptionCode": "WILL_CALL",
            "serviceOptionRoutingCode": None,
            "autoCommit": "true",
            "receiveAmount": {"currencyCode": "USD", "value": 100},
            "sender": {
                "business": {
                    "address": {
                        "city": "ROME",
                        "line1": "Piazza della Liberta",
                        "postalCode": 10001,
                        "countryCode": "USA",
                        "countrySubdivisionCode": "US-NY",
                    },
                    "businessName": "Business",
                    "businessType": "ACCOMMODATION_HOTELS",
                    "contactDetails": {"phone": {"number": 2003004000, "countryDialCode": 1}},
                    "legalEntityName": "Entity",
                    "businessIssueDate": "2013-05-26",
                    "businessRegistrationNumber": "10-2030405",
                    "businessCountryOfRegistration": "USA",
                }
            },
            "beneficiary": {
                "consumer": {
                    "name": {
                        "firstName": "Alen",
                        "lastName": "Smith",
                    },
                    "mobilePhone": {"number": "N/A", "countryDialCode": None},
                }
            },
            "targetAccount": {
                "accountNumber": None,
                "bankName": None,
            },
            "receipt": {
                "primaryLanguage": None,
                "secondaryLanguage": None,
            },
        },
    )


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_status_missing(mg):
    responses._add_from_file(file_path="tests/palpay/responses/status_missing.yaml")
    client = PalPayClient()
    transaction_id = "transaction_id"
    PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    _, response = client.status(transaction_id, agent_partner_id="AAAAAA")
    assert response.status_code == 400
    assert response.data == {"errors": [{"category": "IP-20000", "code": "697", "message": "Invalid Transaction ID"}]}


# @_recorder.record(file_path="tests/palpay/responses/status_ok.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_status_ok(mg):
    responses._add_from_file(file_path="tests/palpay/responses/status_ok.yaml")
    client = PalPayClient()
    transaction_id = "64c228ba-8013-43f6-9baf-a0c87b91a261"
    PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    _, response = client.status(transaction_id, agent_partner_id="AAAAAA")
    assert response.status_code == 200
    assert response.data == {
        "transactionId": "64c228ba-8013-43f6-9baf-a0c87b91a261",
        "referenceNumber": "27380423",
        "transactionSendDateTime": "2024-11-20T07:04:13.814",
        "expectedPayoutDate": "2024-11-20",
        "transactionStatus": "SENT",
        "transactionSubStatus": [],
        "originatingCountryCode": "USA",
        "destinationCountryCode": "PHL",
        "serviceOptionCode": "WILL_CALL",
        "serviceOptionName": "10 Minute Service",
        "sendAmount": {
            "amount": {"value": 300.0, "currencyCode": "USD"},
            "fees": {"value": 9.0, "currencyCode": "USD"},
            "taxes": {"value": 0.0, "currencyCode": "USD"},
            "discountsApplied": {"totalDiscount": {"value": 0.0, "currencyCode": "USD"}},
            "total": {"value": 309.0, "currencyCode": "USD"},
        },
        "receiveAmount": {
            "amount": {"value": 300.0, "currencyCode": "USD"},
            "fees": {"value": 0.0, "currencyCode": "USD"},
            "taxes": {"value": 0, "currencyCode": "USD"},
            "total": {"value": 300.0, "currencyCode": "USD"},
            "fxRate": 1,
        },
        "sender": {
            "businessInfo": {
                "businessName": "TEST",
                "businessRegistrationNumber": "13-1760110",
                "businessCountryOfRegistration": "USA",
            },
            "businessProfileId": "bp-xyz-12345",
        },
        "beneficiary": {"consumer": {"firstName": "Alen", "lastName": "Smith"}},
    }


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_query_status(mg):
    responses._add_from_file(file_path="tests/palpay/responses/status_ok.yaml")
    client = PalPayClient()
    transaction_id = "64c228ba-8013-43f6-9baf-a0c87b91a261"
    pr = PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    client.query_status(transaction_id, agent_partner_id="AAAAAA", update=True)
    pr.refresh_from_db()
    assert pr.payout_amount == 300
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER=67890)
def test_create_transaction(mg):
    responses._add_from_file(file_path="tests/palpay/responses/transaction.yaml")
    client = PalPayClient()
    pr = PaymentRecordFactory(record_code="code-123", parent__fsp=mg)
    payload = {
        "first_name": "Alice",
        "last_name": "Foo",
        "amount": 1000,
        "origination_currency": "USD",
        "destination_country": "NGA",
        "destination_currency": "NGN",
        "payment_record_code": "code-123",
        "phone_no": "+393891234567",
        "agent_partner_id": "AAAAAA",
    }
    _, response = client.create_transaction(payload)
    assert response.status_code == 200
    assert response.data == {
        "transactionId": "18ba47c4-6376-40d4-a0c9-e52722dc52cf",
        "businessProfileId": "bp-xyz-12345",
        "serviceOptionName": "10 Minute Service",
        "referenceNumber": "49122304",
        "expectedPayoutDate": "2024-11-22",
        "sendAmount": {
            "amount": {"value": 1000.0, "currencyCode": "USD"},
            "fees": {"value": 30.0, "currencyCode": "USD"},
            "taxes": {"value": 0.0, "currencyCode": "USD"},
            "discountsApplied": {"totalDiscount": {"value": 0.0, "currencyCode": "USD"}},
            "total": {"value": 1030.0, "currencyCode": "USD"},
        },
        "receiveAmount": {
            "amount": {"value": 741389.6, "currencyCode": "NGN"},
            "fees": {"value": 0.0, "currencyCode": "NGN"},
            "taxes": {"value": 0.0, "currencyCode": "NGN"},
            "total": {"value": 741389.6, "currencyCode": "NGN"},
            "fxRate": 741.3896,
            "fxRateEstimated": False,
        },
    }
    pr.refresh_from_db()
    assert pr.auth_code == "49122304"
    assert pr.fsp_code == "18ba47c4-6376-40d4-a0c9-e52722dc52cf"
    assert pr.success


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (PaymentRecordState.PENDING, SENT),
        (PaymentRecordState.TRANSFERRED_TO_FSP, RECEIVED),
        (PaymentRecordState.TRANSFERRED_TO_FSP, REFUNDED),
        (PaymentRecordState.TRANSFERRED_TO_FSP, DELIVERED),
    ],
)
def test_update_status_ok(from_status, to_status):
    pr = PaymentRecordFactory(status=from_status)
    update_status(pr, to_status)
