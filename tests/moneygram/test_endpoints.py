import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import responses
from constance.test import override_config
from cryptography.exceptions import InvalidSignature
from django.urls import reverse
from factories import PaymentRecordFactory
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=False)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ok(mg, api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status="PENDING", parent__fsp=mg)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP
    assert response.status_code == 200


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=False)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_no_record(mg, api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="xxxxx", status=PaymentRecordState.PENDING, parent__fsp=mg)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"cannot_find_transaction": "Cannot find payment with provided reference 1234567890"}


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=False)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_transition_not_allowed(mg, api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status=PaymentRecordState.REFUND, parent__fsp=mg)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"error": "transition_not_allowed"}


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=True)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_signature(mg, api_client, admin_user, monkeypatch):
    def mock_verify(*args, **kwargs):
        return False

    monkeypatch.setattr("hope_payment_gateway.apps.fsp.moneygram.endpoints.verify", mock_verify)

    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(
        url, data=data, user=admin_user, format="json", HTTP_SIGNATURE="t=1234567890,s=invalid_signature"
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid Signature header"}


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=True)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_signature_exception(mg, api_client, admin_user, monkeypatch):
    def mock_load_pem_public_key(*args, **kwargs):
        mock_key = Mock()
        mock_key.verify.side_effect = InvalidSignature()
        return mock_key

    monkeypatch.setattr("cryptography.hazmat.primitives.serialization.load_pem_public_key", mock_load_pem_public_key)

    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(
        url, data=data, user=admin_user, format="json", HTTP_SIGNATURE="t=1234567890,s=invalid_signature"
    )
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid Signature header"}


@responses.activate
@pytest.mark.django_db
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=False)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_payout_date(mg, api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status=PaymentRecordState.TRANSFERRED_TO_FSP, parent__fsp=mg)
    url = reverse("moneygram:mg-status-webhook")

    data["eventPayload"]["transactionStatus"] = "RECEIVED"
    api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
    assert pr.payout_date is not None
    assert pr.payout_date.strftime("%Y-%m-%d") == "2023-03-27"

    data["eventPayload"]["transactionStatus"] = "DELIVERED"
    api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()

    assert pr.status == PaymentRecordState.TRANSFERRED_TO_BENEFICIARY
    assert pr.payout_date is not None
    assert pr.payout_date.strftime("%Y-%m-%d") == "2023-03-27"
