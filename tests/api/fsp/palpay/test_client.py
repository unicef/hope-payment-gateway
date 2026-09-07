import pytest
import responses
from constance.test import override_config
from django.conf import settings
from rest_framework.response import Response as DRFResponse
from unittest.mock import patch, MagicMock

from factories import PaymentRecordFactory
from responses import _recorder  # noqa
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.api.palpay.client import PalPayClient
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


@pytest.fixture
def pr_invalid_payload(palpay):
    return PaymentRecordFactory.create(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="new-transaction",
        payload={"payment_record_code": "new-transaction"},
    )


@pytest.fixture
def pr_invalid_account(palpay):
    return PaymentRecordFactory.create(
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


@pytest.fixture
def pr_status_ok(palpay):
    return PaymentRecordFactory.create(
        parent__fsp=palpay, record_code="1234566777", payload={"payment_record_code": "1234566777"}
    )


@pytest.fixture
def pr_invalid_status(palpay):
    return PaymentRecordFactory.create(
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


@pytest.fixture
def pr_create_success(palpay):
    return PaymentRecordFactory.create(
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


@pytest.fixture
def pr_create_success_no_update(palpay):
    return PaymentRecordFactory.create(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="new-transaction-no-update",
        payload={
            "payment_record_code": "new-transaction-no-update",
            "account-national_number": "NAT-456",
            "account-city_name": "Ramallah",
            "account-gov_name": "Central",
            "amount": 500,
        },
    )


@pytest.fixture
def pr_global_status(palpay):
    return PaymentRecordFactory.create(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="status-query",
        fsp_code="FSP-CODE-123",
    )


@pytest.fixture
def pr_post_success(palpay):
    return PaymentRecordFactory.create(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="post-ok",
    )


@pytest.fixture
def pr_post_failure(palpay):
    return PaymentRecordFactory.create(
        parent__office=palpay.configs.first().office,
        parent__fsp=palpay,
        record_code="post-ko",
    )


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_get_profile(palpay):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/profile.yaml")
    _, response, _ = PalPayClient().get_profile()
    assert response.status_code == 200
    assert response.json()["Succeeded"]
    assert len(response.json()["Data"]) == 2


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_check_balance(mg):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/check_balance.yaml")
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
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/beneficiary.yaml")
    _, response, _ = PalPayClient().beneficiary()
    jresponse = response.json()
    assert response.status_code == 200
    assert jresponse == {"Succeeded": True, "Message": "", "Data": [], "TotalPages": 0, "Page": 1, "TotalCount": 0}


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_transactions(mg):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/transactions.yaml")
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
def test_create_transaction_ko_invalid_payload(palpay, pr_invalid_payload):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/create_transaction_ko_invalid_payload.yaml")
    _, response, _ = PalPayClient().create_transaction(pr_invalid_payload.payload)
    assert response.status_code == 400
    jresponse = response.data
    assert jresponse["code"] == "validation_error"
    assert jresponse["message"] == "InvalidPayload: account-national_number is missing in the payload"


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_ko_invalid_(palpay, pr_invalid_account):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/create_transaction_ko_invalid_account.yaml")
    _, response, _ = PalPayClient().create_transaction(pr_invalid_account.payload)
    assert response.status_code == 400
    jresponse = response.data
    assert not jresponse["Succeeded"]
    assert jresponse["Message"] == "عذرا تم انشاء طلب الصرف مسبقا"
    assert jresponse["ErrorCode"] == -1003


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_status_ok(palpay, pr_status_ok):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/status_ok.yaml")
    _, response, _ = PalPayClient().status(pr_status_ok.payload)
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
def test_create_transaction_ko_invalid_status(palpay, pr_invalid_status):
    responses._add_from_file(file_path="tests/api/fsp/palpay/responses/create_transaction_ko_invalid_account.yaml")
    with pytest.raises(TransitionNotAllowed, match="Cannot Trigger Transaction: Invalid Status"):
        PalPayClient().create_transaction(pr_invalid_status.payload)


def _make_mock_response(data, status_code=200):
    mock = MagicMock()
    mock.data = data
    mock.status_code = status_code
    mock.json.return_value = data
    return mock


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_success(palpay, pr_create_success):
    data = {"Succeeded": True, "Data": {"TransferId": "T123"}, "Message": "ok"}
    mock_resp = _make_mock_response(data, 200)
    with (
        patch.object(PalPayClient, "perform_request", return_value=mock_resp),
        patch.object(PalPayClient, "post_transaction") as mock_post,
    ):
        payload, response, endpoint = PalPayClient().create_transaction(pr_create_success.payload)
    assert response.status_code == 200
    assert response.data["Succeeded"]
    pr_create_success.refresh_from_db()
    assert pr_create_success.success is True
    assert pr_create_success.status == PaymentRecordState.TRANSFERRED_TO_FSP
    mock_post.assert_called_once_with(response, pr_create_success.payload)


@responses.activate
@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_create_transaction_success_no_update(palpay, pr_create_success_no_update):
    data = {"Succeeded": True, "Data": {"TransferId": "T456"}, "Message": "ok"}
    mock_resp = _make_mock_response(data, 200)
    with (
        patch.object(PalPayClient, "perform_request", return_value=mock_resp),
        patch.object(PalPayClient, "post_transaction") as mock_post,
    ):
        payload, response, endpoint = PalPayClient().create_transaction(
            pr_create_success_no_update.payload, update=False
        )
    assert response.status_code == 200
    assert response.data["Succeeded"]
    pr_create_success_no_update.refresh_from_db()
    assert pr_create_success_no_update.success is True
    mock_post.assert_not_called()


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_global_status(palpay, pr_global_status):
    mock_resp = MagicMock()
    with patch.object(PalPayClient, "perform_request", return_value=mock_resp) as mock_perform:
        endpoint, payload, response = PalPayClient().global_status({"payment_record_code": "status-query"})
    expected_endpoint = f"{settings.PALPAY_HOST}/api/v1/moneytransfer/transactions/"
    assert endpoint == expected_endpoint
    assert payload == {}
    assert response is mock_resp
    mock_perform.assert_called_once_with(expected_endpoint, "FSP-CODE-123", {})


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_post_transaction_success(palpay, pr_post_success):
    body = {"Succeeded": True, "Data": {"TransferId": "T999"}, "Message": "done"}
    response = DRFResponse(body, status=200)
    PalPayClient().post_transaction(response, {"payment_record_code": "post-ok"})
    pr_post_success.refresh_from_db()
    assert pr_post_success.success is True
    assert pr_post_success.auth_code == "T999"
    assert pr_post_success.message == "done"
    assert pr_post_success.status == PaymentRecordState.TRANSFERRED_TO_FSP
    assert pr_post_success.fsp_data == body


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_post_transaction_failure(palpay, pr_post_failure):
    body = {"Succeeded": False, "ErrorCode": -1003, "Message": "error"}
    response = DRFResponse(body, status=200)
    PalPayClient().post_transaction(response, {"payment_record_code": "post-ko"})
    pr_post_failure.refresh_from_db()
    assert pr_post_failure.success is False
    assert pr_post_failure.message == "error [-1003]"
    assert pr_post_failure.status == PaymentRecordState.ERROR
    assert pr_post_failure.fsp_data == body
