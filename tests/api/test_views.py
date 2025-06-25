import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from factories import PaymentRecordFactory
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState
from viewflow.fsm import TransitionNotAllowed

from tests.factories import (
    SystemFactory,
    DeliveryMechanismFactory,
    PaymentInstructionFactory,
    ExportTemplateFactory,
    OfficeFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action", "detail", "status"),
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
    ("action", "detail", "status"),
    [
        ("open", True, 200),
        ("ready", True, 400),
        ("close", True, 400),
        ("process", True, 400),
        ("finalize", True, 400),
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
    "payload",
    [
        "{}",
        '{"config_key": "tester_one", "destination_country": "ES"}',
    ],
)
def _test_payment_instruction_create(api_client, token_user, mg, payload):
    user, token = token_user
    SystemFactory.create(owner=user)
    url = reverse("rest:payment-instruction-list")
    data = {
        "remote_id": "123456",
        "external_code": "654321",
        "active": True,
        "status": "DRAFT",
        "fsp": mg.id,
        "payload": payload,
    }
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True, data=data)
    assert view.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"config_key": "tester_one", "destination_country": "ES"}',
    ],
)
def test_payment_instruction_create(api_client, token_user, mg, payload):
    _test_payment_instruction_create(api_client, token_user, mg, payload)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"config_key": "tester_one", "destination_country": "ES"}',
    ],
)
def test_payment_instruction_create_with_office(api_client, token_user, mg, payload):
    OfficeFactory.create(code="tester_one", supervised=True)
    _test_payment_instruction_create(api_client, token_user, mg, payload)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action", "detail", "status"),
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
@patch("hope_payment_gateway.apps.fsp.western_union.api.client.WesternUnionClient.refund")
def test_payment_record_cancel(mock_refund, api_client, token_user, mg):
    user, token = token_user
    pr = PaymentRecordFactory()
    url = reverse("rest:payment-record-cancel", args=[pr.remote_id])

    mock_refund.side_effect = None
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token)

    assert view.status_code == 200


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.fsp.western_union.api.client.WesternUnionClient.refund")
def test_payment_record_cancel_fail(mock_refund, api_client, token_user, mg):
    user, token = token_user
    pr = PaymentRecordFactory()
    url = reverse("rest:payment-record-cancel", args=[pr.remote_id])

    mock_refund.side_effect = TransitionNotAllowed("Cannot cancel this record")
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token)

    assert view.status_code == 400


@pytest.mark.django_db
def test_instructions_add_records_ok(api_client, token_user):
    user, token = token_user
    pr = PaymentRecordFactory(parent__status=PaymentInstructionState.OPEN)
    url = reverse("rest:payment-instruction-add-records", args=[pr.parent.remote_id])
    payload = [
        {
            "record_code": "adalberto",
            "remote_id": "adalberto",
            "payload": {"key": "value"},
        },
    ]
    view = api_client.post(
        url,
        json.dumps(payload),
        content_type="application/json",
        user=user,
        HTTP_AUTHORIZATION=token,
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


@pytest.mark.django_db
def test_payment_instruction_download_fail(api_client, token_user):
    user, token = token_user
    instruction_instance = PaymentInstructionFactory(payload={"delivery_mechanism": "tester_one"})
    pr = PaymentRecordFactory(parent=instruction_instance)
    DeliveryMechanismFactory.create(code="tester_one")
    url = reverse("rest:payment-instruction-download", args=[pr.parent.remote_id])
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)

    assert view.status_code == 400
    assert view.data.get("status_error") == "ExportTemplate matching query does not exist."


@pytest.mark.django_db
def test_payment_instruction_download(api_client, token_user):
    user, token = token_user
    pi = PaymentInstructionFactory(payload={"delivery_mechanism": "tester_one", "config_key": "123456"})
    pr = PaymentRecordFactory.create(parent=pi)
    dm = DeliveryMechanismFactory.create(code="tester_one")
    ExportTemplateFactory.create(fsp=pi.fsp, config_key="123456", delivery_mechanism=dm)
    url = reverse("rest:payment-instruction-download", args=[pr.parent.remote_id])
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)

    assert view.status_code == 200


@pytest.mark.django_db
def test_health_check(api_client, token_user):
    url = "http://testserver/health"

    view = api_client.get(url)

    assert view.status_code == 200
    assert view.text == "OK"
