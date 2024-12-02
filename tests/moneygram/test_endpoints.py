import json
from pathlib import Path

from django.urls import reverse

import pytest
import responses
from constance.test import override_config
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
@override_config(MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED=False)
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_webhook_notification_ko_invalid_payload(mg, api_client, admin_user):
    with open(Path(__file__).parent / "responses" / "push_notification_ko.json") as f:
        data = json.load(f)

    pr = PaymentRecordFactory(fsp_code="1234567890", status=PaymentRecordState.REFUND, parent__fsp=mg)
    url = reverse("moneygram:mg-status-webhook")
    response = api_client.post(url, data=data, user=admin_user, format="json")
    pr.refresh_from_db()
    assert response.status_code == 400
    assert response.data == {"cannot_retrieve ID": "missing eventPayload > transactionId"}
