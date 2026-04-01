from datetime import date
from unittest.mock import patch

import pytest
from constance.test import override_config
from django.urls import reverse
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.api.palpay.views import PalPayWebhook
from hope_payment_gateway.apps.fsp.palpay import RECEIVED
from tests.factories import PaymentRecordFactory


def _build_payload(
    transaction_id: str,
    transaction_status: str = RECEIVED,
    status_date: str = "2026-01-02T03:04:05.678900",
):
    return {
        "eventId": "evt-123",
        "eventDate": "2026-01-01T01:02:03.123456",
        "subscriptionType": "TRANSACTION_STATUS_EVENT",
        "eventPayload": {
            "transactionId": transaction_id,
            "transactionStatus": transaction_status,
            "transactionStatusDate": status_date,
            "transactionSubStatus": [
                {"subStatus": "SUCCESS", "message": "Delivered"},
                {"subStatus": "INFO", "message": "Processed"},
            ],
        },
    }


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ", WHITELIST_ENABLED=False)
def test_palpay_webhook_post_success_updates_record(api_client, palpay):
    pr = PaymentRecordFactory(parent__fsp=palpay, fsp_code="trx-001", payout_date=None)
    payload = _build_payload(transaction_id="trx-001")

    response = api_client.post(reverse("pal:palpay-status-webhook"), data=payload, format="json")

    assert response.status_code == 200
    assert response.json() == payload
    pr.refresh_from_db()
    assert pr.payout_date == date(2026, 1, 2)
    assert pr.extra_data["eventId"] == payload["eventId"]
    assert pr.extra_data["eventDate"] == payload["eventDate"]
    assert pr.extra_data["subscriptionType"] == payload["subscriptionType"]
    assert pr.extra_data["transactionSubStatus"] == [
        {"status": "SUCCESS", "message": "Delivered"},
        {"status": "INFO", "message": "Processed"},
    ]


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ", WHITELIST_ENABLED=False)
def test_palpay_webhook_post_returns_400_when_record_missing(api_client):
    payload = _build_payload(transaction_id="unknown-trx")

    response = api_client.post(reverse("pal:palpay-status-webhook"), data=payload, format="json")

    assert response.status_code == 400
    assert response.json() == {"cannot_find_transaction": "Cannot find payment with provided reference unknown-trx"}


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ", WHITELIST_ENABLED=False)
def test_palpay_webhook_post_returns_400_on_transition_not_allowed(api_client, palpay):
    PaymentRecordFactory(parent__fsp=palpay, fsp_code="trx-002")
    payload = _build_payload(transaction_id="trx-002")

    with patch.object(PalPayWebhook, "update_record", side_effect=TransitionNotAllowed):
        response = api_client.post(reverse("pal:palpay-status-webhook"), data=payload, format="json")

    assert response.status_code == 400
    assert response.json() == {"error": "transition_not_allowed"}


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ", WHITELIST_ENABLED=False)
def test_palpay_webhook_dispatch_captures_sentry_message(api_client, palpay):
    PaymentRecordFactory(parent__fsp=palpay, fsp_code="trx-003")
    payload = _build_payload(transaction_id="trx-003")

    with patch("hope_payment_gateway.api.palpay.views.sentry_sdk.capture_message") as mock_capture:
        response = api_client.post(reverse("pal:palpay-status-webhook"), data=payload, format="json")

    assert response.status_code == 200
    mock_capture.assert_called_once_with("PalPay: Webhook Notification")


@pytest.mark.django_db
def test_palpay_update_record_sets_data_and_payout_date():
    pr = PaymentRecordFactory(extra_data={})
    payload = _build_payload(transaction_id="trx-004")

    PalPayWebhook.update_record(pr, payload)

    pr.refresh_from_db()
    assert pr.payout_date == date(2026, 1, 2)
    assert pr.extra_data["transactionSubStatus"] == [
        {"status": "SUCCESS", "message": "Delivered"},
        {"status": "INFO", "message": "Processed"},
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status_date",
    [
        "bad-date-format",
        None,
    ],
)
def test_palpay_update_record_suppresses_invalid_or_missing_status_date(status_date):
    pr = PaymentRecordFactory(extra_data={})
    payload = _build_payload(transaction_id="trx-005")
    if status_date is None:
        payload["eventPayload"].pop("transactionStatusDate")
    else:
        payload["eventPayload"]["transactionStatusDate"] = status_date

    PalPayWebhook.update_record(pr, payload)

    pr.refresh_from_db()
    assert pr.payout_date is None
    assert pr.extra_data["eventId"] == payload["eventId"]
