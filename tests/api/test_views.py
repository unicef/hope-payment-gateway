import json

from django.urls import reverse

import pytest

from hope_payment_gateway.apps.gateway.models import PaymentInstruction
from tests.factories import PaymentRecordFactory


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_instruction(api_client_with_credentials, token_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.uuid])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = api_client_with_credentials.get(url, user=token_user, expect_errors=True)
    assert view.status_code == status


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
def test_payment_instruction_actions(api_client_with_credentials, token_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.uuid])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = api_client_with_credentials.post(url, user=token_user, expect_errors=True)
    assert view.status_code == status


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_record_list(api_client_with_credentials, token_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-record-{action}", args=[pr.uuid])
    else:
        url = reverse(f"rest:payment-record-{action}")
    view = api_client_with_credentials.get(url, user=token_user)
    assert view.status_code == status


def test_instructions_add_records_ok(api_client_with_credentials, token_user):
    pr = PaymentRecordFactory(parent__status=PaymentInstruction.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.uuid])
    payload = [
        {"record_code": "adalberto", "payload": {"key": "value"}},
    ]
    view = api_client_with_credentials.post(url, json.dumps(payload), user=token_user, content_type="application/json")
    assert view.status_code == 201
    assert view.json()["uuid"] == pr.parent.uuid
    assert "adalberto" in view.json()["records"]


def test_instructions_add_records_ko(api_client_with_credentials, token_user):
    pr = PaymentRecordFactory(parent__status=PaymentInstruction.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.uuid])
    payload = [
        {
            "record_code": "alfio",
            "payload": None,
        },
        {
            "record_code": "baldo",
            "payload": {"key": "value"},
        },
        {
            "record_code": None,
            "payload": {"key": "value"},
        },
    ]
    view = api_client_with_credentials.post(
        url, json.dumps(payload), user=token_user, content_type="application/json", expect_errors=True
    )
    assert view.status_code == 400
    assert view.json()["uuid"] == pr.parent.uuid
    assert view.json()["errors"] == {
        "2": {"record_code": ["This field may not be null."]},
    }


def test_instructions_add_records_invalid_status(api_client_with_credentials, token_user):
    pr = PaymentRecordFactory(parent__status=PaymentInstruction.ABORTED)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.uuid])
    view = api_client_with_credentials.post(url, user=token_user, expect_errors=True)
    assert view.status_code == 400
    assert view.json()["message"] == "Cannot add records to a not Open Plan"
    assert view.json()["status"] == "ABORTED"
