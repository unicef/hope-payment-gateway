import pytest
import responses
from constance.test import override_config

from factories import PaymentRecordFactory
from responses import _recorder  # noqa
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.palpay.client import PalPayClient
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_get_profile(palpay):
    responses._add_from_file(file_path="tests/palpay/responses/profile.yaml")
    _, response, _ = PalPayClient().get_profile()
    assert response.status_code == 200
    assert response.json()["Succeeded"]
    assert len(response.json()["Data"]) == 2


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_check_balance(mg):
    responses._add_from_file(file_path="tests/palpay/responses/check_balance.yaml")
    _, response, _ = PalPayClient().balance()
    jresponse = response.json()
    assert response.status_code == 200
    assert jresponse["Data"] == [
        {"ProfileName": "ILS ", "ProfileId": 1, "Currency": "شيكل", "CurrentBalance": 50000.0},
        {"ProfileName": "USD ", "ProfileId": 2, "Currency": "دولار", "CurrentBalance": 50000.0},
    ]
    assert not jresponse["Failed"]
    assert jresponse["Succeeded"]


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_beneficiary(mg):
    responses._add_from_file(file_path="tests/palpay/responses/beneficiary.yaml")
    _, response, _ = PalPayClient().beneficiary()
    jresponse = response.json()
    assert response.status_code == 200
    assert jresponse == {"Succeeded": True, "Message": "", "Data": [], "TotalPages": 0, "Page": 1, "TotalCount": 0}


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_transactions(mg):
    responses._add_from_file(file_path="tests/palpay/responses/transactions.yaml")
    _, response, _ = PalPayClient().transactions()
    jresponse = response.json()
    assert response.status_code == 200
    assert jresponse["Succeeded"] == 1
    assert jresponse["TotalPages"] == 1
    assert jresponse["Page"] == 1
    assert jresponse["TotalCount"] == 4
    assert len(jresponse["Data"]) == 4


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_ko_invalid_payload(palpay):
    responses._add_from_file(file_path="tests/palpay/responses/create_transaction_ko_invalid_payload.yaml")
    pr = PaymentRecordFactory(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="new-transaction",
        payload={"payment_record_code": "new-transaction"},
    )
    _, response, _ = PalPayClient().create_transaction(pr.payload)
    assert response.status_code == 400
    jresponse = response.data
    assert jresponse["code"] == "validation_error"
    assert jresponse["message"] == "InvalidPayload: account-national_number is missing in the payload"


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_ko_invalid_(palpay):
    responses._add_from_file(file_path="tests/palpay/responses/create_transaction_ko_invalid_account.yaml")
    pr = PaymentRecordFactory(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="new-transaction",
        payload={
            "payment_record_code": "new-transaction",
            "account-national_number": "NAT-123",
            "account-city_name": "Rome",
            "account-gov_name": "Lazio",
            "amount": 1000,
        },
    )
    _, response, _ = PalPayClient().create_transaction(pr.payload)
    assert response.status_code == 400
    jresponse = response.data
    assert not jresponse["Succeeded"]
    assert jresponse["Message"] == "عذرا تم انشاء طلب الصرف مسبقا"
    assert jresponse["ErrorCode"] == -1003


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_status_ok(palpay):
    responses._add_from_file(file_path="tests/palpay/responses/status_ok.yaml")
    pr = PaymentRecordFactory(
        parent__fsp=palpay, record_code="1234566777", payload={"payment_record_code": "1234566777"}
    )
    _, response, _ = PalPayClient().status(pr.payload)
    jresponse = response.json()
    assert response.status_code == 200
    assert response.json()["Succeeded"]
    assert jresponse["Data"] == {
        "Id": 1137,
        "TraDate": "2025-09-05T18:06:07",
        "TransRefNo": "None",
        "TransferName": "12345",
        "Mobile": "0590000005",
        "PalpayAccount": "100000949173376",
        "FullPalpayAccount": "100000949173376014000",
        "SalaryAmount": 0.0,
        "CurrencyCode": "376",
        "ProfileId": 51,
        "Status": 5,
        "StatusText": "Error Check Wallet",
    }


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_ko_invalid_status(palpay):
    responses._add_from_file(file_path="tests/palpay/responses/create_transaction_ko_invalid_account.yaml")
    pr = PaymentRecordFactory(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="new-transaction",
        payload={
            "payment_record_code": "new-transaction",
            "account-national_number": "NAT-123",
            "account-city_name": "Rome",
            "account-gov_name": "Lazio",
            "amount": 1000,
        },
        status=PaymentRecordState.TRANSFERRED_TO_FSP,
    )
    with pytest.raises(TransitionNotAllowed, match="Cannot Trigger Transaction: Invalid Status"):
        PalPayClient().create_transaction(pr.payload)
