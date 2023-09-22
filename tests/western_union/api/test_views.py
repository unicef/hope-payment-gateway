import json

from django.urls import reverse

import pytest

from hope_payment_gateway.apps.western_union.models import PaymentInstruction
from tests.factories import PaymentRecordFactory


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
        ("open", True, 200),
        ("ready", True, 400),
        ("close", True, 400),
        ("cancel", True, 200),
    ],
)
def test_payment_instruction_list(django_app, admin_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.uuid])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = django_app.get(url, user=admin_user, expect_errors=True)
    assert view.status_code == status


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_record_list(django_app, admin_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-record-{action}", args=[pr.uuid])
    else:
        url = reverse(f"rest:payment-record-{action}")
    view = django_app.get(url, user=admin_user)
    assert view.status_code == status


def test_instructions_add_records_ok(django_app, admin_user):
    pr = PaymentRecordFactory(parent__status=PaymentInstruction.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.uuid])
    payload = [
        {"record_code": "adalberto", "payload": {"key": "value"}},
    ]
    view = django_app.post(url, json.dumps(payload), user=admin_user, content_type="application/json")
    assert view.status_code == 201
    assert view.json_body["uuid"] == pr.parent.uuid
    assert "adalberto" in view.json_body["records"]


def test_instructions_add_records_ko(django_app, admin_user):
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
    view = django_app.post(
        url, json.dumps(payload), user=admin_user, content_type="application/json", expect_errors=True
    )
    assert view.status_code == 400
    assert view.json_body["uuid"] == pr.parent.uuid
    assert view.json_body["errors"] == {
        "0": {"payload": ["This field may not be null."]},
        "2": {"record_code": ["This field may not be null."]},
    }


def test_instructions_add_records_invalid_status(django_app, admin_user):
    pr = PaymentRecordFactory(parent__status=PaymentInstruction.CANCELLED)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.uuid])
    view = django_app.post(url, user=admin_user, expect_errors=True)
    assert view.status_code == 400
    assert view.json_body["message"] == "Cannot add records to a not Open Plan"
    assert view.json_body["status"] == "CANCELLED"
