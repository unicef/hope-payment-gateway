import json

from django.urls import reverse

import pytest
from factories import PaymentRecordFactory

from hope_payment_gateway.apps.gateway.models import PaymentInstruction, PaymentInstructionState


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_instruction(api_client, action, detail, status, token_user):
    user, token = token_user
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.remote_id])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == status


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("open", True, 200),
        ("ready", True, 400),
        ("close", True, 400),
        ("process", True, 400),
        ("abort", True, 200),
    ],
)
def test_payment_instruction_actions(api_client, action, detail, status, token_user):
    user, token = token_user
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.remote_id])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == status


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_record_list(api_client, action, detail, status, token_user):
    user, token = token_user
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-record-{action}", args=[pr.remote_id])
    else:
        url = reverse(f"rest:payment-record-{action}")
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token)
    assert view.status_code == status


@pytest.mark.django_db
def test_instructions_add_records_ok(api_client, token_user):
    user, token = token_user
    pr = PaymentRecordFactory(parent__status=PaymentInstructionState.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.remote_id])
    payload = [
        {"record_code": "adalberto", "remote_id": "adalberto", "payload": {"key": "value"}},
    ]
    view = api_client.post(
        url, json.dumps(payload), content_type="application/json", user=user, HTTP_AUTHORIZATION=token
    )
    assert view.status_code == 201
    assert view.json()["remote_id"] == pr.parent.remote_id
    assert "adalberto" in view.json()["records"]


@pytest.mark.django_db
def test_instructions_add_records_ko(api_client, token_user):
    user, token = token_user
    pr = PaymentRecordFactory(parent__status=PaymentInstructionState.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.remote_id])
    payload = [
        {
            "record_code": "alfio",
            "remote_id": "alfio",
            "payload": None,
        },
        {
            "record_code": "baldo",
            "remote_id": None,
            "payload": {"key": "value"},
        },
        {
            "record_code": None,
            "remote_id": "alfio",
            "payload": {"key": "value"},
        },
    ]
    view = api_client.post(
        url,
        json.dumps(payload),
        content_type="application/json",
        user=user,
        HTTP_AUTHORIZATION=token,
        expect_errors=True,
    )
    assert view.status_code == 400
    assert view.json()["remote_id"] == pr.parent.remote_id
    assert view.json()["errors"] == {
        "1": {"remote_id": ["This field may not be null."]},
        "2": {"record_code": ["This field may not be null."]},
    }


@pytest.mark.django_db
def test_instructions_add_records_invalid_status(api_client, token_user):
    user, token = token_user
    pr = PaymentRecordFactory(parent__status=PaymentInstructionState.ABORTED)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.remote_id])
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == 400
    assert view.json()["message"] == "Cannot add records to a not Open Plan"
    assert view.json()["status"] == "ABORTED"
