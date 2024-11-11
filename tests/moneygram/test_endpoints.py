import json
from pathlib import Path

from django.urls import reverse

import responses
from factories import PaymentRecordFactory

from hope_payment_gateway.apps.gateway.models import PaymentRecordState


@responses.activate
def test_webhook_notification_ok(api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status="PENDING")
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert pr.status == PaymentRecordState.TRANSFERRED_TO_FSP
    assert response.status_code == 200


@responses.activate
def test_webhook_notification_ko_no_record(api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="xxxxx", status=PaymentRecordState.PENDING)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"cannot_find_transaction": "Cannot find payment with provided reference 1234567890"}


@responses.activate
def test_webhook_notification_ko_transition_not_allowed(api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status=PaymentRecordState.REFUND)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"error": "transition_not_allowed"}


@responses.activate
def test_webhook_notification_ko_invalid_payload(api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification_ko.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status=PaymentRecordState.REFUND)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"cannot_retrieve ID": "missing eventPayload > transactionId"}
