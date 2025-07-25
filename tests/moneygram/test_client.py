from unittest.mock import Mock

import pytest
import requests
import responses
from constance.test import override_config
from django.conf import settings
from factories import PaymentRecordFactory
from hope_payment_gateway.apps.fsp.exceptions import InvalidTokenError, PayloadMissingKeyError
from hope_payment_gateway.apps.fsp.moneygram import (
    DELIVERED,
    RECEIVED,
    REFUNDED,
    UNFUNDED,
    AVAILABLE,
    REJECTED,
    CLOSED,
)
from hope_payment_gateway.apps.fsp.moneygram.client import (
    MoneyGramClient,
    update_status,
)
from hope_payment_gateway.apps.gateway.models import PaymentRecordState
from responses import _recorder  # noqa
from rest_framework.response import Response
from viewflow.fsm import TransitionNotAllowed


# @_recorder.record(file_path="tests/moneygram/responses/token.yaml")
# Override Agent Partner ID


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_token_ko(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token_ko.yaml")
    with pytest.raises(InvalidTokenError):
        MoneyGramClient()


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_token(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    assert client.token == "HMfWVGb6AYGmx3B07JSXsfIZQw6Z"
    assert client.expires_in == "3599"


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_headers_token(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    assert client.get_headers("request_id") == {
        "Content-Type": "application/json",
        "X-MG-ClientRequestId": "request_id",
        "content-type": "application/json",
        "Authorization": "Bearer HMfWVGb6AYGmx3B07JSXsfIZQw6Z",
    }


@pytest.mark.django_db
@responses.activate
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_basic_payload(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    assert client.get_basic_payload(agent_partner_id="AAAAAA") == {
        "targetAudience": "AGENT_FACING",
        "agentPartnerId": "AAAAAA",
        "userLanguage": "en-US",
    }


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_prepare_transactions(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
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
        "account": {
            "number": "+94786661137",
        },
    }
    assert client.prepare_transaction(pr.get_payload()) == (
        pr_code,
        {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": "AAAAAA",
            "userLanguage": "en-US",
            "destinationCountryCode": "IT",
            "partnerTransactionId": "test-code",
            "sendCurrencyCode": "USD",
            "serviceOptionCode": "WILL_CALL",
            "serviceOptionRoutingCode": None,
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
                    "mobilePhone": {"number": 786661137, "countryDialCode": 94},
                }
            },
            "targetAccount": {
                "accountNumber": "+94786661137",
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
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_prepare_quote(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        "first_name": "Alen",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "US",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    assert client.prepare_quote(pr.get_payload()) == (
        "test-code",
        {
            "targetAudience": "AGENT_FACING",
            "agentPartnerId": "AAAAAA",
            "userLanguage": "en-US",
            "destinationCountryCode": "US",
            "serviceOptionCode": "WILL_CALL",
            "beneficiaryTypeCode": "Consumer",
            "receiveAmount": {"currencyCode": "USD", "value": 100},
        },
    )


# @_recorder.record(file_path="tests/moneygram/responses/quote.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_quote(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/quote.yaml")
    client = MoneyGramClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        "first_name": "Alen",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "MEX",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "delivery_services_code": "WILL_CALL",
        "agent_partner_id": "AAAAAA",
    }
    _, response, _ = client.quote(pr.get_payload())
    assert response.data == {
        "transactions": [
            {
                "transactionId": "f3ba1025-6247-4ae6-90b4-1bdfc2da527d",
                "serviceOptionCode": "WILL_CALL",
                "serviceOptionName": "10 Minute Service",
                "estimatedDelivery": "A Few Minutes",
                "sendAmount": {
                    "amount": {"value": 100.0, "currencyCode": "USD"},
                    "fees": {"value": 3.0, "currencyCode": "USD"},
                    "taxes": {"value": 0.0, "currencyCode": "USD"},
                    "total": {"value": 103.0, "currencyCode": "USD"},
                },
                "receiveAmount": {
                    "amount": {"value": 1638.0, "currencyCode": "MXN"},
                    "fees": {"value": 0.0, "currencyCode": "MXN"},
                    "taxes": {"value": 0.0, "currencyCode": "MXN"},
                    "total": {"value": 1638.0, "currencyCode": "MXN"},
                    "fxRate": 16.37874,
                    "fxRateEstimated": False,
                },
            }
        ]
    }


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_status_missing(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/status_missing.yaml")
    client = MoneyGramClient()
    transaction_id = "transaction_id"
    record = PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    payload = {"agent_partner_id": "AAAAAA", "payment_record_code": record.record_code}
    _, response, _ = client.status(payload)
    assert response.status_code == 400
    assert response.data == {"errors": [{"category": "IP-20000", "code": "697", "message": "Invalid Transaction ID"}]}


# @_recorder.record(file_path="tests/moneygram/responses/status_ok.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_status_ok(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/status_ok.yaml")
    client = MoneyGramClient()
    transaction_id = "64c228ba-8013-43f6-9baf-a0c87b91a261"
    record = PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    payload = {"agent_partner_id": "AAAAAA", "payment_record_code": record.record_code}
    _, response, _ = client.status(payload)
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
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_status(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/status_ok.yaml")
    client = MoneyGramClient()
    transaction_id = "64c228ba-8013-43f6-9baf-a0c87b91a261"
    pr = PaymentRecordFactory(fsp_code=transaction_id, parent__fsp=mg)
    payload = {"agent_partner_id": "AAAAAA", "payment_record_code": pr.record_code}
    client.status_update(payload)
    pr.refresh_from_db()
    assert pr.payout_amount == 300
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_draft_transaction(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/transaction.yaml")
    client = MoneyGramClient()
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
    _, response, _ = client.draft_transaction(payload)
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
    assert pr.fsp_code == "18ba47c4-6376-40d4-a0c9-e52722dc52cf"
    assert pr.success


# @_recorder.record(file_path="tests/moneygram/responses/refund.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_refund(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/refund.yaml")
    client = MoneyGramClient()
    transaction_id = "a0ea837d-af5b-4cdd-8ac1-560477bf0978"
    pr = PaymentRecordFactory(
        fsp_code=transaction_id,
        payload={"refuse_reason_code": "DUP_TRAN", "agent_partner_id": "AAAAAA"},
        parent__fsp=mg,
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    _, resp, _ = client.refund(pr.get_payload())
    pr.refresh_from_db()
    assert pr.message == "Refunded Duplicate Transaction"
    assert pr.status == PaymentRecordState.REFUND
    assert resp.status_code == 200


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_required_fields(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/required_fields.yaml")
    client = MoneyGramClient()
    payload = {
        "delivery_mechanism": "bank_account",
        "service_provider_code": "BANK_DEPOSIT",
        "service_provider_routing_code": "74826841",
        "amount": 100,
        "origination_currency": "USD",
        "destination_country": "NGA",
        "destination_currency": "NGN",
        "agent_partner_id": "AAAAAA",
    }
    pr = PaymentRecordFactory(payload=payload, parent__fsp=mg)
    _, response, _ = client.get_required_fields(payload)
    pr.refresh_from_db()
    assert response.status_code == 200
    assert response.data == {
        "destinationCountryCode": "NGA",
        "amount": 100.0,
        "sendCurrencyCode": "USD",
        "receiveCurrencyCode": "NGN",
        "serviceOptionCode": "BANK_DEPOSIT",
        "serviceOptionName": "Bank Deposit - All Banks",
        "serviceOptionRoutingCode": "74826841",
        "serviceOptionRoutingName": "All Banks",
        "fieldInfo": [
            {
                "field": "destinationCountryCode",
                "dataType": "cntrycode",
                "required": True,
                "fieldLabel": "Destination Country",
                "displayOrder": "1",
                "fieldMin": "0",
                "fieldMax": "3",
            },
            {
                "field": "destinationCountrySubdivisionCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Destination State/Province",
                "displayOrder": "5",
            },
            {
                "field": "fundInStore.fundInStore",
                "dataType": "boolean",
                "required": True,
                "fieldLabel": "Transaction Staging",
                "displayOrder": "19",
            },
            {
                "field": "fundInStore.fundInStoreAgentPartnerId",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "8",
            },
            {
                "field": "fundingSource.accountIdentifier",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "55",
            },
            {
                "field": "fundingSource.provider",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "55",
            },
            {
                "field": "fundingSource.providerAccountNumber",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "55",
            },
            {
                "field": "fundingSource.providerNetworkCode",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "55",
            },
            {
                "field": "fundingSource.tenderType",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "30",
            },
            {
                "field": "receipt.primaryLanguage",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Primary Receipt Language",
                "displayOrder": "13",
            },
            {
                "field": "receipt.secondaryLanguage",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Secondary Receipt Language",
                "displayOrder": "14",
            },
            {
                "field": "receiveCurrencyCode",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Receive Currency",
                "displayOrder": "20",
                "fieldMin": "0",
                "fieldMax": "3",
            },
            {
                "field": "receiver.address.city",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver City",
                "displayOrder": "13",
                "fieldMin": "0",
                "fieldMax": "40",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
            },
            {
                "field": "receiver.address.countryCode",
                "dataType": "cntrycode",
                "required": False,
                "fieldLabel": "Receiver Country",
                "displayOrder": "14",
                "fieldMin": "3",
                "fieldMax": "3",
            },
            {
                "field": "receiver.address.countrySubdivisionCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver State",
                "displayOrder": "15",
                "fieldMin": "0",
                "fieldMax": "2",
            },
            {
                "field": "receiver.address.line1",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Street Address",
                "displayOrder": "9",
                "fieldMin": "0",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed. "
                "Minimum 5 characters with at least one alpha character. "
                "No repeated special characters ( #### or ////). PO Box not allowed",
            },
            {
                "field": "receiver.address.line2",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Street Address 2",
                "displayOrder": "10",
                "fieldMin": "0",
                "fieldMax": "80",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed",
            },
            {
                "field": "receiver.address.line3",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Street Address 3",
                "displayOrder": "11",
                "fieldMin": "0",
                "fieldMax": "80",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed",
            },
            {
                "field": "receiver.address.postalCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver ZIP Code",
                "displayOrder": "16",
                "fieldMin": "0",
                "fieldMax": "10",
                "regEx": "^[0-9a-zA-Z -]*$",
            },
            {
                "field": "receiver.mobilePhone.countryDialCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Mobile Number Country Code",
                "displayOrder": "17",
                "fieldMin": "0",
                "fieldMax": "5",
            },
            {
                "field": "receiver.mobilePhone.number",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Mobile Number",
                "displayOrder": "18",
                "fieldMin": "5",
                "fieldMax": "14",
                "helpTextLong": "Only numeric characters are allowed. "
                "Cannot contain a string of repeating numeric characters (example 8888888)",
            },
            {
                "field": "receiver.name.firstName",
                "dataType": "string",
                "required": True,
                "fieldLabel": "First/Given Name",
                "displayOrder": "1",
                "fieldMin": "1",
                "fieldMax": "20",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "receiver.name.lastName",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Last/Family Name",
                "displayOrder": "3",
                "fieldMin": "1",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "receiver.name.middleName",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Middle Name",
                "displayOrder": "4",
                "fieldMin": "0",
                "fieldMax": "20",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "receiver.name.secondLastName",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Second Last/Family Name",
                "displayOrder": "6",
                "fieldMin": "1",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {"field": "receiverSameAsSender", "dataType": "boolean", "required": False},
            {
                "field": "rewardsNumber",
                "dataType": "string",
                "required": False,
                "fieldLabel": "MoneyGram Plus Number",
                "displayOrder": "1",
                "fieldMax": "20",
                "regEx": "^[0-9]*$",
            },
            {
                "field": "sendAmount.currencyCode",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Send Currency",
                "displayOrder": "19",
                "fieldMin": "0",
                "fieldMax": "20",
            },
            {
                "field": "sendAmount.value",
                "dataType": "decimal",
                "required": True,
                "fieldLabel": "Amount",
                "displayOrder": "18",
                "fieldMin": "0",
                "fieldMax": "20",
            },
            {
                "field": "sender.address.city",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Sender City",
                "displayOrder": "11",
                "fieldMin": "0",
                "fieldMax": "40",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
            },
            {
                "field": "sender.address.countryCode",
                "dataType": "cntrycode",
                "required": True,
                "fieldLabel": "Sender Country",
                "displayOrder": "12",
                "fieldMin": "3",
                "fieldMax": "3",
            },
            {
                "field": "sender.address.countrySubdivisionCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Sender State",
                "displayOrder": "13",
                "fieldMin": "0",
                "fieldMax": "25",
            },
            {
                "field": "sender.address.line1",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Sender Street Address",
                "displayOrder": "8",
                "fieldMin": "0",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed. "
                "Minimum 5 characters with at least one alpha character. "
                "No repeated special characters ( #### or ////). PO Box not allowed",
            },
            {
                "field": "sender.address.line2",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Sender Street Address 2",
                "displayOrder": "9",
                "fieldMin": "0",
                "fieldMax": "80",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed",
            },
            {
                "field": "sender.address.line3",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Address Line 3",
                "displayOrder": "10",
                "fieldMax": "80",
                "regEx": "^([a-zA-Z0-9 \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
                "helpTextLong": "Only alpha, numeric and certain special characters (#./'-,()\") are allowed",
            },
            {
                "field": "sender.address.postalCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Sender Zip Code",
                "displayOrder": "14",
                "fieldMin": "0",
                "fieldMax": "10",
                "regEx": "^[0-9a-zA-Z -]*$",
            },
            {
                "field": "sender.email",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Email",
                "displayOrder": "20",
                "fieldMax": "255",
                "regEx": "^(([\\\\.a-zA-Z0-9_\\\\-])+@([a-zA-Z0-9_\\\\-])+([a-zA-Z0-9_\\\\-])+"
                "[\\\\.]{1}([a-zA-Z0-9_\\\\-])+[\\\\.]?([a-zA-Z0-9_\\\\-])+)*$",
            },
            {
                "field": "sender.enrolInRewards",
                "dataType": "boolean",
                "required": False,
            },
            {
                "field": "sender.mobilePhone.countryDialCode",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Primary Phone Country Code",
                "displayOrder": "14",
                "fieldMax": "5",
            },
            {
                "field": "sender.mobilePhone.number",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Primary Phone Number",
                "displayOrder": "15",
                "fieldMin": "6",
                "fieldMax": "14",
                "regEx": "^([0-9\\.\\-])*$",
                "helpTextLong": "Only numeric characters are allowed."
                " Cannot contain a string of repeating numeric characters (example 8888888)",
            },
            {
                "field": "sender.name.firstName",
                "dataType": "string",
                "required": True,
                "fieldLabel": "First/Given Name",
                "displayOrder": "1",
                "fieldMin": "1",
                "fieldMax": "20",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "sender.name.lastName",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Last/Family Name",
                "displayOrder": "3",
                "fieldMin": "1",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "sender.name.middleName",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Middle Name",
                "displayOrder": "2",
                "fieldMax": "20",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "sender.name.secondLastName",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Second Last/Family Name",
                "displayOrder": "4",
                "fieldMin": "1",
                "fieldMax": "30",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\-\\'\\/])*$",
                "helpTextLong": "Cannot start with special character, cannot contain number. "
                "Only alpha characters, dash (-) and apostrophe (') allowed",
            },
            {
                "field": "sender.notificationLanguagePreference",
                "dataType": "string",
                "required": False,
                "fieldMin": "0",
                "fieldMax": "5",
            },
            {
                "field": "sender.notificationPreferences.optIn",
                "dataType": "boolean",
                "required": False,
                "fieldLabel": "Sender Transaction Email Notification Opt-In",
                "displayOrder": "30",
            },
            {
                "field": "sender.notificationPreferences.optIn",
                "dataType": "boolean",
                "required": False,
                "fieldLabel": "Sender Marketing SMS Notification Opt-In",
                "displayOrder": "32",
            },
            {
                "field": "sender.notificationPreferences.optIn",
                "dataType": "boolean",
                "required": False,
                "fieldLabel": "Sender Marketing Email Notification Opt-In",
                "displayOrder": "31",
            },
            {
                "field": "sender.personalDetails.birthCity",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Birth City",
                "displayOrder": "26",
                "fieldMax": "40",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
            },
            {
                "field": "sender.personalDetails.birthCountryCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Birth Country",
                "displayOrder": "25",
                "fieldMin": "3",
                "fieldMax": "3",
            },
            {
                "field": "sender.personalDetails.citizenshipCountryCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Country of Citizenship",
                "displayOrder": "32",
                "fieldMin": "3",
                "fieldMax": "3",
            },
            {
                "field": "sender.personalDetails.dateOfBirth",
                "dataType": "date",
                "required": True,
                "fieldLabel": "Sender Date of Birth",
                "displayOrder": "21",
                "fieldMin": "0",
                "fieldMax": "30",
            },
            {
                "field": "sender.personalDetails.genderCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Gender",
                "displayOrder": "21",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "MALE", "description": "Male"},
                    {"value": "FEMALE", "description": "Female"},
                    {"value": "UNKNOWN", "description": "Not Known / Not Given"},
                ],
            },
            {
                "field": "sender.personalDetails.occupationCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Occupation",
                "displayOrder": "22",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "ADMIN", "description": "Administrative"},
                    {"value": "AGRICULTURE", "description": "Agriculture"},
                    {"value": "AUTOMOTIVE_SALES", "description": "Automotive"},
                    {"value": "BANKING", "description": "Financial Services"},
                    {"value": "CLERGY", "description": "Religious"},
                    {"value": "COMPUTER", "description": "Information Technology (IT)"},
                    {"value": "CUSTOMER_CARE", "description": "Customer Care/Retail"},
                    {"value": "EDUCATION", "description": "Education"},
                    {"value": "ENGINEER", "description": "Engineer"},
                    {"value": "FACTORY", "description": "Physical Worker"},
                    {"value": "HEALTH_SERVICES", "description": "Healthcare"},
                    {"value": "PUBLIC_OFFICIAL", "description": "Public Servant"},
                    {"value": "RESTAURANT", "description": "Restaurant"},
                    {"value": "RETIRED", "description": "Retiree"},
                    {"value": "STUDENT", "description": "Student"},
                    {"value": "UNEMPLOYED", "description": "Unemployed/Homemaker"},
                    {"value": "CONSULTING", "description": "Consulting"},
                    {"value": "ENTERTAINMENT", "description": "Entertainment"},
                    {"value": "EXECUTIVE", "description": "Executive"},
                    {"value": "EXPLICIT_SERVICES", "description": "Explicit Services"},
                    {"value": "HUMAN_RESOURCES", "description": "Human Resources"},
                    {"value": "LEGAL", "description": "Legal"},
                    {"value": "PERSONAL_SERVICES", "description": "Personal Services"},
                    {"value": "SPORT", "description": "Sport"},
                    {"value": "ENTREPRENEUR", "description": "Entrepreneur"},
                ],
            },
            {
                "field": "sender.primaryIdentification.expirationDay",
                "dataType": "gDay",
                "required": False,
                "fieldLabel": "ID Expiry Day",
                "displayOrder": "8",
                "exampleText": "dd",
            },
            {
                "field": "sender.primaryIdentification.expirationMonth",
                "dataType": "gMonth",
                "required": False,
                "fieldLabel": "ID Expiry Month",
                "displayOrder": "7",
                "exampleText": "mm",
            },
            {
                "field": "sender.primaryIdentification.expirationYear",
                "dataType": "gYear",
                "required": False,
                "fieldLabel": "ID Expiry Year",
                "displayOrder": "6",
                "exampleText": "yyyy",
            },
            {
                "field": "sender.primaryIdentification.id",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Sender ID Number",
                "displayOrder": "2",
                "fieldMin": "0",
                "fieldMax": "25",
            },
            {
                "field": "sender.primaryIdentification.issueAuthority",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "ID Issue Authority",
                "displayOrder": "12",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "AB", "description": "Agency or Bureau"},
                    {"value": "CO", "description": "Commissioners Office"},
                    {"value": "CON", "description": "Consulate"},
                    {"value": "COR", "description": "Corporation"},
                    {"value": "EMB", "description": "Embassy"},
                ],
            },
            {
                "field": "sender.primaryIdentification.issueCity",
                "dataType": "string",
                "required": False,
                "fieldLabel": "ID Issue City",
                "displayOrder": "11",
                "fieldMax": "40",
                "regEx": "^([a-zA-Z \\u00C0-\\u017F\\#\\/\\.\\\"\\'\\,\\(\\)\\-])*$",
            },
            {
                "field": "sender.primaryIdentification.issueCountryCode",
                "dataType": "cntrycode",
                "required": True,
                "fieldLabel": "Sender ID Country",
                "displayOrder": "3",
                "fieldMin": "3",
                "fieldMax": "3",
            },
            {
                "field": "sender.primaryIdentification.issueCountrySubdivisionCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Sender ID State",
                "displayOrder": "4",
                "fieldMin": "0",
                "fieldMax": "40",
            },
            {
                "field": "sender.primaryIdentification.issueDay",
                "dataType": "gDay",
                "required": False,
                "fieldLabel": "ID Issue Day",
                "displayOrder": "5",
            },
            {
                "field": "sender.primaryIdentification.issueMonth",
                "dataType": "gMonth",
                "required": False,
                "fieldLabel": "ID Issue Month",
                "displayOrder": "4",
            },
            {
                "field": "sender.primaryIdentification.issueYear",
                "dataType": "gYear",
                "required": False,
                "fieldLabel": "ID Issue Year",
                "displayOrder": "3",
            },
            {
                "field": "sender.primaryIdentification.typeCode",
                "dataType": "enum",
                "required": True,
                "fieldLabel": "Sender ID Type",
                "displayOrder": "1",
                "fieldMin": "0",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "ALN", "description": "Alien ID"},
                    {"value": "DRV", "description": "Drivers License"},
                    {"value": "GOV", "description": "Government ID"},
                    {"value": "PAS", "description": "Passport"},
                    {"value": "STA", "description": "State ID"},
                ],
            },
            {
                "field": "sender.secondaryIdentification.expirationDay",
                "dataType": "gDay",
                "required": False,
                "fieldLabel": "Secondary ID Expiry Day",
                "displayOrder": "8",
                "exampleText": "dd",
            },
            {
                "field": "sender.secondaryIdentification.expirationMonth",
                "dataType": "gMonth",
                "required": False,
                "fieldLabel": "Secondary ID Expiry Month",
                "displayOrder": "7",
                "exampleText": "mm",
            },
            {
                "field": "sender.secondaryIdentification.expirationYear",
                "dataType": "gYear",
                "required": False,
                "fieldLabel": "Secondary ID Expiry Year",
                "displayOrder": "6",
                "exampleText": "yyyy",
            },
            {
                "field": "sender.secondaryIdentification.id",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Sender Secondary ID Number",
                "displayOrder": "14",
                "fieldMin": "0",
                "fieldMax": "20",
            },
            {
                "field": "sender.secondaryIdentification.issueAuthority",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Secondary ID Issue Authority",
                "displayOrder": "12",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "AB", "description": "Agency or Bureau"},
                    {"value": "CO", "description": "Commissioners Office"},
                    {"value": "CON", "description": "Consulate"},
                    {"value": "COR", "description": "Corporation"},
                    {"value": "EMB", "description": "Embassy"},
                ],
            },
            {
                "field": "sender.secondaryIdentification.issueCountryCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Secondary ID Issue Country",
                "displayOrder": "9",
            },
            {
                "field": "sender.secondaryIdentification.issueCountrySubdivisionCode",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Secondary ID Issue State/Province",
                "displayOrder": "10",
            },
            {
                "field": "sender.secondaryIdentification.issueDay",
                "dataType": "gDay",
                "required": False,
                "fieldLabel": "Secondary ID Issue Day",
                "displayOrder": "5",
            },
            {
                "field": "sender.secondaryIdentification.issueMonth",
                "dataType": "gMonth",
                "required": False,
                "fieldLabel": "Secondary ID Issue Month",
                "displayOrder": "4",
            },
            {
                "field": "sender.secondaryIdentification.issueYear",
                "dataType": "gYear",
                "required": False,
                "fieldLabel": "Secondary ID Issue Year",
                "displayOrder": "3",
            },
            {
                "field": "sender.secondaryIdentification.typeCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Sender Secondary ID Type",
                "displayOrder": "13",
                "fieldMin": "0",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "ALN", "description": "Alien ID"},
                    {"value": "INT", "description": "International ID"},
                    {"value": "SSN", "description": "Social Security Number"},
                    {"value": "TAX", "description": "Tax ID"},
                ],
            },
            {
                "field": "serviceOptionCode",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Service Option",
                "displayOrder": "8",
            },
            {
                "field": "serviceOptionRoutingCode",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Receive Agent ID",
                "displayOrder": "17",
                "fieldMin": "0",
                "fieldMax": "20",
            },
            {
                "field": "targetAccount.accountNumber",
                "dataType": "string",
                "required": True,
                "fieldLabel": "NUBAN",
                "displayOrder": "8",
                "fieldMin": "10",
                "fieldMax": "11",
                "regEx": "[0-9]*",
            },
            {
                "field": "targetAccount.bankName",
                "dataType": "string",
                "required": True,
                "fieldLabel": "Bank Name",
                "displayOrder": "3",
                "fieldMin": "3",
                "fieldMax": "7",
                "enumerationItem": [
                    {"value": "100003", "description": "9 PAYMENT SERVICE BANK"},
                    {"value": "100011", "description": "AB MICROFINANCE BANK"},
                    {"value": "000014", "description": "ACCESS BANK"},
                    {"value": "100008", "description": "ACCION MICROFINANCE BANK"},
                    {"value": "000009", "description": "CITI BANK"},
                    {"value": "000010", "description": "ECOBANK"},
                    {"value": "100001", "description": "ENTERPRISE BANK"},
                    {
                        "value": "100006",
                        "description": "FAIRMONEY MICROFINANCE BANK LTD",
                    },
                    {"value": "000003", "description": "FCMB"},
                    {"value": "000007", "description": "FIDELITY BANK"},
                    {"value": "100010", "description": "FINA TRUST MICROFINANCE BANK"},
                    {"value": "000016", "description": "FIRST BANK OF NIGERIA"},
                    {"value": "000027", "description": "GLOBUS BANK"},
                    {"value": "000034", "description": "SIGNATURE BANK LTD"},
                    {"value": "000013", "description": "GUARANTY TRUST BANK"},
                    {"value": "000020", "description": "HERITAGE BANK"},
                    {"value": "000006", "description": "JAIZ BANK"},
                    {"value": "000002", "description": "KEYSTONE BANK"},
                    {"value": "100004", "description": "KUDA MICRO-FINANCE BANK"},
                    {"value": "100007", "description": "LAPO MICROFINANCE BANK"},
                    {"value": "000029", "description": "LOTUS BANK"},
                    {"value": "100013", "description": "LOVONUS MICROFINANCE BANK"},
                    {
                        "value": "100009",
                        "description": "MUTUAL TRUST MICROFINANCE BANK",
                    },
                    {"value": "000036", "description": "OPTIMUS BANK"},
                    {"value": "000030", "description": "PARALLEX BANK"},
                    {"value": "000008", "description": "POLARIS BANK LTD"},
                    {"value": "000031", "description": "PREMIUM TRUST BANK"},
                    {"value": "000023", "description": "PROVIDUS BANK"},
                    {"value": "100012", "description": "SPARKLE MICRO-FINANCE BANK"},
                    {"value": "000012", "description": "STANBIC IBTC BANK"},
                    {
                        "value": "000021",
                        "description": "STANDARD CHARTERED BANK NIGERIA LTD",
                    },
                    {"value": "000001", "description": "STERLING BANK"},
                    {"value": "000022", "description": "SUNTRUST BANK NIGERIA LIMITED"},
                    {"value": "100002", "description": "TAJ BANK"},
                    {"value": "000025", "description": "TITAN TRUST BANK LTD"},
                    {"value": "000018", "description": "UNION BANK"},
                    {"value": "000004", "description": "UNITED BANK FOR AFRICA"},
                    {"value": "000011", "description": "UNITY BANK"},
                    {"value": "100005", "description": "VFD MICRO-FINANCE BANK"},
                    {"value": "000017", "description": "WEMA BANK"},
                    {"value": "000015", "description": "ZENITH BANK"},
                ],
            },
            {
                "field": "targetAccountprofileid",
                "dataType": "string",
                "required": False,
                "fieldLabel": "Receiver Registration Number (RRN)",
                "displayOrder": "16",
                "fieldMin": "0",
                "fieldMax": "20",
            },
            {
                "field": "transactionInformation.intendedUseOfMGIServicesCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Why do you typically use MoneyGram?",
                "displayOrder": "10",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "BUSINESS_RELATED", "description": "Business-Related"},
                    {"value": "CHARITY_SUPPORT", "description": "Charity Support"},
                    {
                        "value": "FAMILY_FRIENDS_SUPPORT",
                        "description": "Family/Friend Support",
                    },
                    {"value": "THIRD_PARTY", "description": "Third Party"},
                ],
            },
            {
                "field": "transactionInformation.proofOfFundsCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Proof of Funds",
                "displayOrder": "1",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "ACT_OF_ATTORNEY", "description": "Act of Attorney"},
                    {
                        "value": "BANK_STATEMENT",
                        "description": "Bank account statement/withdrawl slip",
                    },
                    {"value": "NATIONAL_LOTTERY", "description": "Copy of Check"},
                    {"value": "PAYROLL_SLIP", "description": "Payroll slip"},
                    {"value": "SALE_CERTIFICATE", "description": "Sales certificate"},
                    {"value": "TAX_NOTICE", "description": "Income Tax Notice"},
                ],
            },
            {
                "field": "transactionInformation.purposeOfTransactionCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Purpose of Transaction",
                "displayOrder": "7",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "BUSINESS_EXPENSE", "description": "Business Expense"},
                    {"value": "DONATION", "description": "Donation"},
                    {"value": "EDUCATION_TRAIN", "description": "Education"},
                    {"value": "GIFT", "description": "Gift"},
                    {"value": "INVEST_SAVING", "description": "Investment"},
                    {"value": "LEGAL_OBLIGATION", "description": "Legal Obligation"},
                    {"value": "LOAN", "description": "Loan"},
                    {"value": "TRAVEL_EXPENSES", "description": "Travel Expenses"},
                    {"value": "BILLS", "description": "Bills"},
                    {"value": "FOOD", "description": "Food"},
                    {"value": "MEDICAL", "description": "Medical Expenses"},
                    {
                        "value": "PURCHASE_GOODS",
                        "description": "Payment for Goods/Services",
                    },
                    {"value": "PERSONAL_USE", "description": "Personal Need/Expense"},
                    {"value": "SALARY", "description": "Salary"},
                ],
            },
            {
                "field": "transactionInformation.relationshipToReceiver",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Relationship to Receiver",
                "displayOrder": "5",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "ACQUAINTANCE", "description": "Acquaintance"},
                    {"value": "BUSINESS_PARTNER", "description": "Business Partner"},
                    {"value": "CLIENT", "description": "Client"},
                    {"value": "EMPLOY_EMPLOYER", "description": "Employee"},
                    {"value": "FAMILY", "description": "Family Member"},
                    {"value": "FRIEND", "description": "Close Friend"},
                    {"value": "CONTRACTOR", "description": "Contractor"},
                    {"value": "EMPLOYER", "description": "Employer"},
                    {"value": "MYSELF", "description": "Myself"},
                    {"value": "ONLINE_FRIEND", "description": "Online Friend"},
                    {"value": "THIRD_PARTY", "description": "Third Party"},
                    {"value": "VENDOR", "description": "Vendor"},
                ],
            },
            {
                "field": "transactionInformation.sourceOfFundsCode",
                "dataType": "enum",
                "required": False,
                "fieldLabel": "Source of Funds",
                "displayOrder": "3",
                "fieldMax": "30",
                "enumerationItem": [
                    {"value": "LOAN", "description": "Loan"},
                    {"value": "SAVINGS", "description": "Savings"},
                    {"value": "SALE_OF_PROPERTY", "description": "Sale of Property"},
                    {"value": "SALARY_EMPLOY", "description": "Salary"},
                    {"value": "FAMILY_FUNDS", "description": "Family Funds"},
                    {"value": "INHERITANCE", "description": "Inheritance"},
                    {"value": "LOTTERY_GAMBLING", "description": "Lottery/Gambling"},
                    {"value": "PENSION", "description": "Pension"},
                    {"value": "SOCIAL_BENEFITS", "description": "Social Benefits"},
                    {"value": "THIRD_PARTY", "description": "Third Party"},
                ],
            },
        ],
    }


# @_recorder.record(file_path="tests/moneygram/responses/service_options.yaml")
@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_get_service_options(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/service_options.yaml")
    client = MoneyGramClient()
    _, response, _ = client.get_service_options({"agent_partner_id": "AAAAAA", "destination_country": "NGA"})
    assert response.status_code == 200
    assert response.data == [
        {
            "destinationCountryCode": "NGA",
            "serviceOptions": [
                {
                    "serviceOptionCode": "WILL_CALL",
                    "destinationCurrencyCode": "NGN",
                    "serviceOptionName": "10 Minute Service",
                    "serviceOptionDisplayDescription": " ",
                    "serviceOptionCategoryId": "1",
                    "serviceOptionCategoryDisplayName": "RECEIVE CASH",
                    "maxReceiveAmount": "2500000",
                    "localCurrency": "USD",
                    "indicativeRateAvailable": False,
                },
                {
                    "serviceOptionCode": "BANK_DEPOSIT",
                    "destinationCurrencyCode": "NGN",
                    "serviceOptionRoutingCode": "74826841",
                    "serviceOptionName": "Bank Deposit - All Banks",
                    "serviceOptionDisplayDescription": " ",
                    "serviceOptionCategoryId": "2",
                    "serviceOptionCategoryDisplayName": "ACCOUNT DEPOSIT",
                    "maxReceiveAmount": "7000000",
                    "serviceOptionRoutingName": "All Banks",
                    "localCurrency": "USD",
                    "indicativeRateAvailable": False,
                },
                {
                    "serviceOptionCode": "DIRECT_TO_ACCT",
                    "destinationCurrencyCode": "NGN",
                    "serviceOptionRoutingCode": "75388278",
                    "serviceOptionName": "Mobile Wallet Deposit - SmartCash / Airtel",
                    "serviceOptionDisplayDescription": "Delivery Option 19: Direct to Account",
                    "serviceOptionCategoryId": "2",
                    "serviceOptionCategoryDisplayName": "ACCOUNT DEPOSIT",
                    "maxReceiveAmount": "5000000",
                    "serviceOptionRoutingName": "SmartCash / Airtel",
                    "localCurrency": "USD",
                    "indicativeRateAvailable": False,
                },
            ],
        }
    ]


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_set_token_connection_error(mg):
    MoneyGramClient._instances = {}  # MoneyGram client is singleton
    url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
    responses.add(responses.GET, url, body=ConnectionError("Connection error occurred"), status=400)

    client = MoneyGramClient()
    assert client.token is None


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_set_token_expires_in(mg):
    MoneyGramClient._instances = {}  # Clear singleton instance
    url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
    mock_response = {"access_token": "test_token", "expires_in": "3600", "token_type": "Bearer"}
    responses.add(responses.GET, url, json=mock_response, status=200)
    client = MoneyGramClient()
    assert client.expires_in == "3600"


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_set_token_invalid_error(mg):
    MoneyGramClient._instances = {}  # Clear singleton instance
    url = settings.MONEYGRAM_HOST + "/oauth/accesstoken?grant_type=client_credentials"
    mock_error_response = {"error": {"category": "AUTHENTICATION", "message": "Invalid credentials", "code": "401"}}
    responses.add(responses.GET, url, json=mock_error_response, status=401)
    with pytest.raises(InvalidTokenError) as exc_info:
        MoneyGramClient()
    assert str(exc_info.value) == "AUTHENTICATION: Invalid credentials  [401]"


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_prepare_transaction_with_middle_name(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        "first_name": "Alen",
        "middle_name": "John",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    _, payload = client.prepare_transaction(pr.get_payload())
    assert payload["beneficiary"]["consumer"]["name"]["middleName"] == "John"


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_prepare_transaction_with_second_last_name(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        "first_name": "Alen",
        "last_name": "Smith",
        "second_last_name": "Johnson",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    _, payload = client.prepare_transaction(pr.get_payload())
    assert payload["beneficiary"]["consumer"]["name"]["second_last_name"] == "Johnson"


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_prepare_transaction_missing_required_field(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr_code = "test-code"
    pr = PaymentRecordFactory(record_code=pr_code, parent__fsp=mg)
    pr.payload = {
        # Missing first_name which is required
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    with pytest.raises(PayloadMissingKeyError) as exc_info:
        client.prepare_transaction(pr.get_payload())
    assert "first_name" in str(exc_info.value)


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_draft_transaction_missing_key_error(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr = PaymentRecordFactory(parent__fsp=mg)
    pr.payload = {
        # Missing required first_name field
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
    }
    _, response, _ = client.draft_transaction(pr.get_payload())
    assert response.status_code == 400
    assert response.data == {
        "context": [{"code": "validation_error", "message": "InvalidPayload: first_name is missing in the payload"}]
    }
    pr.refresh_from_db()
    assert pr.message == "Error"
    assert not pr.success


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_draft_transaction_error_response(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr = PaymentRecordFactory(parent__fsp=mg)
    pr.payload = {
        "first_name": "John",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
        "payment_record_code": pr.record_code,
    }

    _, prepared_payload = client.prepare_transaction(pr.get_payload())
    prepared_payload["payment_record_code"] = pr.record_code

    error_response = {
        "errors": [
            {"code": "INVALID_AMOUNT", "message": "Amount is invalid"},
            {"code": "INVALID_CURRENCY", "message": "Currency is invalid"},
        ]
    }
    responses.add(responses.POST, f"{settings.MONEYGRAM_HOST}/transactions", json=error_response, status=400)

    _, response, _ = client.draft_transaction(prepared_payload)
    assert response.status_code == 400
    pr.refresh_from_db()
    assert pr.message == "Error"
    assert not pr.success


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_perform_request_request_exception(mg, monkeypatch):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()

    def mock_request(*args, **kwargs):
        raise requests.exceptions.RequestException("Request failed")

    monkeypatch.setattr(requests, "request", mock_request)

    response = client.perform_request("/test", "test-id", {}, "get")
    assert response is None


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_perform_request_missing_schema(mg, monkeypatch):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()

    def mock_request(*args, **kwargs):
        raise requests.exceptions.MissingSchema("No schema supplied")

    monkeypatch.setattr(requests, "request", mock_request)

    response = client.perform_request("/test", "test-id", {}, "get")
    assert response is None


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_perform_request_no_response(mg, monkeypatch):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()

    def mock_request(*args, **kwargs):
        return None

    monkeypatch.setattr(requests, "request", mock_request)

    response = client.perform_request("/test", "test-id", {}, "get")
    assert response is None


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_post_transaction_with_errors(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    client = MoneyGramClient()
    pr = PaymentRecordFactory(parent__fsp=mg)
    pr.payload = {
        "first_name": "John",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
        "payment_record_code": pr.record_code,
    }

    error_response = {"errors": [{"code": "INVALID_AMOUNT", "message": "Amount is invalid"}]}

    response = client.post_commit(Response(error_response, status=200), pr.get_payload())
    assert response.status_code == 400
    assert response.data == error_response


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_post_transaction_transition_not_allowed(mg, monkeypatch):
    client = MoneyGramClient()
    pr = PaymentRecordFactory(parent__fsp=mg, fsp_code="18ba47c4-6376-40d4-a0c9-e52722dc52cf")
    pr.payload = {
        "first_name": "John",
        "last_name": "Smith",
        "amount": 100,
        "destination_country": "IT",
        "destination_currency": "USD",
        "origination_country": "US",
        "origination_currency": "USD",
        "agent_partner_id": "AAAAAA",
        "payment_record_code": pr.record_code,
    }

    success_response = Response(
        {
            "referenceNumber": "12345",
            "transactionId": "18ba47c4-6376-40d4-a0c9-e52722dc52cf",
            "receiveAmount": {
                "fees": {"value": 10, "currencyCode": "USD"},
                "taxes": {"value": 5, "currencyCode": "USD"},
                "fxRate": 1.0,
                "fxRateEstimated": False,
            },
            "expectedPayoutDate": "2024-05-04",
        },
        status=200,
    )

    class MockPaymentRecordFlow:
        def __init__(self, payment_record):
            self.payment_record = payment_record

        def store(self):
            raise TransitionNotAllowed("Transition not allowed")

    monkeypatch.setattr("hope_payment_gateway.apps.fsp.moneygram.client.PaymentRecordFlow", MockPaymentRecordFlow)
    response = client.post_commit(success_response, pr.get_payload())

    assert response.status_code == 400
    assert response.data == {"errors": [{"error": "transition_not_allowed"}]}


def _test_update_status(mg, monkeypatch, status, flow_method_name=None, initial_status=None):
    pr = PaymentRecordFactory(parent__fsp=mg, status=initial_status)
    original_status = pr.status

    if flow_method_name:
        mock_flow = Mock()
        mock_method = Mock()
        setattr(mock_flow, flow_method_name, mock_method)

        def mock_flow_init(payment_record):
            return mock_flow

        monkeypatch.setattr("hope_payment_gateway.apps.fsp.moneygram.client.PaymentRecordFlow", mock_flow_init)

    update_status(pr, status)
    pr.refresh_from_db()
    assert pr.status == original_status  # Status should remain unchanged

    if flow_method_name:
        getattr(mock_flow, flow_method_name).assert_called_once()


@pytest.mark.django_db
def test_update_status_unfunded(mg):
    _test_update_status(mg, None, UNFUNDED, initial_status=PaymentRecordState.PENDING)


@pytest.mark.django_db
def test_update_status_available(mg):
    _test_update_status(mg, None, AVAILABLE, initial_status=PaymentRecordState.TRANSFERRED_TO_FSP)


@pytest.mark.django_db
def test_update_status_rejected(mg, monkeypatch):
    _test_update_status(mg, monkeypatch, REJECTED, "purge", initial_status=PaymentRecordState.TRANSFERRED_TO_FSP)


@pytest.mark.django_db
def test_update_status_refunded(mg, monkeypatch):
    _test_update_status(mg, monkeypatch, REFUNDED, "refund", initial_status=PaymentRecordState.TRANSFERRED_TO_FSP)


@pytest.mark.django_db
def test_update_status_closed(mg, monkeypatch):
    _test_update_status(mg, monkeypatch, CLOSED, "fail", initial_status=PaymentRecordState.PENDING)


@pytest.mark.django_db
def test_update_status_received(mg, monkeypatch):
    _test_update_status(mg, monkeypatch, RECEIVED, "confirm", initial_status=PaymentRecordState.TRANSFERRED_TO_FSP)


@pytest.mark.django_db
def test_update_status_delivered(mg, monkeypatch):
    _test_update_status(mg, monkeypatch, DELIVERED, "confirm", initial_status=PaymentRecordState.TRANSFERRED_TO_FSP)


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_create_transaction(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/transaction_commit.yaml")
    client = MoneyGramClient()
    pr = PaymentRecordFactory(
        record_code="code-123",
        parent__fsp=mg,
        payload={
            "first_name": "Alice",
            "last_name": "Foo",
            "amount": 1000,
            "origination_currency": "USD",
            "destination_country": "NGA",
            "destination_currency": "NGN",
            "payment_record_code": "code-123",
            "phone_no": "+393891234567",
            "agent_partner_id": "AAAAAA",
        },
    )

    _, response, _ = client.create_transaction(pr.get_payload())
    assert response.status_code == 200
    assert response.data == {"referenceNumber": "99067959"}
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER=67890)
def test_commit_transaction(mg):
    responses._add_from_file(file_path="tests/moneygram/responses/token.yaml")
    responses._add_from_file(file_path="tests/moneygram/responses/transaction_commit.yaml")
    client = MoneyGramClient()
    pr = PaymentRecordFactory(record_code="code-123", parent__fsp=mg, fsp_code="369cc376-b172-4616-a1c0-0fdc23305558")
    _, response, _ = client.commit_transaction(pr.get_payload())
    assert response.status_code == 200
    assert response.data == {"referenceNumber": "99067959"}
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP
