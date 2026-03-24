import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from factories import FinancialServiceProviderConfigFactory, PaymentRecordFactory
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.gateway.models import PaymentInstructionState, PaymentInstruction
from tests.factories import (
    DeliveryMechanismFactory,
    ExportTemplateFactory,
    OfficeFactory,
    PaymentInstructionFactory,
    SystemFactory,
    FinancialServiceProviderFactory,
    CountryFactory,
)


@pytest.fixture
def mock_messages():
    with (
        patch("django.contrib.messages.info") as mock_info,
        patch("django.contrib.messages.error") as mock_error,
        patch("django.contrib.messages.warning") as mock_warning,
        patch("django.contrib.messages.success") as mock_success,
    ):
        yield {"info": mock_info, "error": mock_error, "warning": mock_warning, "success": mock_success}


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
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
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
    OfficeFactory.create(
        code="tester_one",
        supervised=True,
    )
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
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token)
    assert view.status_code == status


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_payment_record_cancel(mock_refund, api_client, token_user, mg):
    user, token = token_user
    pr = PaymentRecordFactory()
    url = reverse("rest:payment-record-cancel", args=[pr.remote_id])

    mock_refund.side_effect = None
    api_client.force_authenticate(user=user, token=token)
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token)

    assert view.status_code == 200


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_payment_record_cancel_fail(mock_refund, api_client, token_user, mg):
    user, token = token_user
    pr = PaymentRecordFactory()
    url = reverse("rest:payment-record-cancel", args=[pr.remote_id])

    mock_refund.side_effect = TransitionNotAllowed("Cannot cancel this record")
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
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
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)

    assert view.status_code == 400
    assert view.data.get("status_error") == "No template found"


@pytest.mark.django_db
def test_payment_instruction_download(api_client, token_user):
    user, token = token_user
    fsp_config = FinancialServiceProviderConfigFactory.create()
    ExportTemplateFactory.create(
        fsp=fsp_config.fsp,
        config_key="123456",
        delivery_mechanism=fsp_config.delivery_mechanism,
        country=fsp_config.country,
        office=fsp_config.office,
    )
    pi = PaymentInstructionFactory(
        fsp=fsp_config.fsp,
        payload={"config_key": "123456"},
        country=fsp_config.country,
        office=fsp_config.office,
        delivery_mechanism=fsp_config.delivery_mechanism,
    )
    pr = PaymentRecordFactory.create(parent=pi)
    url = reverse("rest:payment-instruction-download", args=[pr.parent.remote_id])
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == 200


@pytest.mark.django_db
def test_health_check(api_client, token_user):
    url = "http://testserver/health"

    view = api_client.get(url)

    assert view.status_code == 200
    assert view.text == "OK"


@pytest.mark.django_db
def test_payment_instruction_serializer_update(api_client, token_user):
    user, token = token_user
    system = SystemFactory(owner=user)
    fsp = FinancialServiceProviderFactory()
    remote_id = "existing_remote_id"

    # Create existing instruction
    instruction = PaymentInstructionFactory(system=system, fsp=fsp, remote_id=remote_id, payload={"initial": "data"})

    url = reverse("rest:payment-instruction-list")
    data = {"remote_id": remote_id, "fsp": fsp.id, "payload": {"updated": "data"}, "external_code": "new_code"}

    api_client.force_authenticate(user=user, token=token)
    response = api_client.post(url, data=data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    instruction.refresh_from_db()
    # Verify it was updated, not a new one created
    assert instruction.payload == {"updated": "data"}
    assert instruction.external_code == "new_code"
    assert PaymentInstruction.objects.filter(remote_id=remote_id, system=system).count() == 1


@pytest.mark.django_db
def test_payment_instruction_perform_create_with_office_and_country(api_client, token_user):
    user, token = token_user
    system = SystemFactory(owner=user)
    fsp = FinancialServiceProviderFactory()

    # Pre-create countries to avoid IntegrityError due to missing required fields in get_or_create
    CountryFactory(iso_code2="US", iso_code3="USA", iso_num="840", name="USA")
    CountryFactory(iso_code2="FR", iso_code3="FRA", iso_num="250", name="France")

    # Supervised office
    OfficeFactory(code="supervised_office", supervised=True)

    url = reverse("rest:payment-instruction-list")
    data = {
        "remote_id": "new_remote_id_1",
        "fsp": fsp.id,
        "payload": {"config_key": "supervised_office", "destination_country": "US"},
        "external_code": "code1",
    }

    api_client.force_authenticate(user=user, token=token)
    response = api_client.post(url, data=data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    instruction = PaymentInstruction.objects.get(remote_id="new_remote_id_1", system=system)

    assert instruction.office.code == "supervised_office"
    assert instruction.office.supervised is True
    assert instruction.active is False
    assert instruction.country.iso_code2 == "US"

    # Non-supervised office and new country
    data2 = {
        "remote_id": "new_remote_id_2",
        "fsp": fsp.id,
        "payload": {"config_key": "new_office", "destination_country": "FR"},
        "external_code": "code2",
    }
    response = api_client.post(url, data=data2, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    instruction2 = PaymentInstruction.objects.get(remote_id="new_remote_id_2", system=system)
    assert instruction2.office.code == "new_office"
    assert instruction2.office.supervised is False
    assert instruction2.active is True
    assert instruction2.country.iso_code2 == "FR"


@pytest.mark.django_db
def test_payment_instruction_perform_create_no_destination_country(api_client, token_user):
    user, token = token_user
    system = SystemFactory(owner=user)
    fsp = FinancialServiceProviderFactory()

    url = reverse("rest:payment-instruction-list")
    data = {
        "remote_id": "new_remote_id_3",
        "fsp": fsp.id,
        "payload": {"config_key": "office_only"},
        "external_code": "code3",
    }

    api_client.force_authenticate(user=user, token=token)
    response = api_client.post(url, data=data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    instruction = PaymentInstruction.objects.get(remote_id="new_remote_id_3", system=system)
    assert instruction.office.code == "office_only"
    assert instruction.country is None
