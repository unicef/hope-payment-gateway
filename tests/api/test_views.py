import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from factories import (
    FinancialServiceProviderConfigFactory,
    PaymentRecordFactory,
    CorridorFactory,
    ServiceProviderCodeFactory,
)
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.gateway.models import PaymentInstructionState, PaymentInstruction
from tests.factories import (
    AccountTypeFactory,
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


@pytest.fixture
def payment_record():
    return PaymentRecordFactory.create()


@pytest.fixture
def open_payment_record():
    return PaymentRecordFactory.create(parent__status=PaymentInstructionState.OPEN)


@pytest.fixture
def aborted_payment_record():
    return PaymentRecordFactory.create(parent__status=PaymentInstructionState.ABORTED)


@pytest.fixture
def system(token_user):
    user, _ = token_user
    return SystemFactory.create(owner=user)


@pytest.fixture
def supervised_office():
    return OfficeFactory.create(code="tester_one", supervised=True)


@pytest.fixture
def download_fail_setup():
    instruction_instance = PaymentInstructionFactory.create(payload={"delivery_mechanism": "tester_one"})
    pr = PaymentRecordFactory.create(parent=instruction_instance)
    DeliveryMechanismFactory.create(code="tester_one")
    return pr


@pytest.fixture
def download_setup():
    fsp_config = FinancialServiceProviderConfigFactory.create()
    ExportTemplateFactory.create(
        fsp=fsp_config.fsp,
        config_key="123456",
        delivery_mechanism=fsp_config.delivery_mechanism,
        country=fsp_config.country,
        office=fsp_config.office,
    )
    pi = PaymentInstructionFactory.create(
        fsp=fsp_config.fsp,
        payload={"config_key": "123456"},
        country=fsp_config.country,
        office=fsp_config.office,
        delivery_mechanism=fsp_config.delivery_mechanism,
    )
    PaymentRecordFactory.create(parent=pi)
    return pi


@pytest.fixture
def download_requires_email_setup(token_user):
    user, _ = token_user
    user.email = ""
    user.save(update_fields=["email"])
    fsp_config = FinancialServiceProviderConfigFactory.create()
    export_template = ExportTemplateFactory.create(
        fsp=fsp_config.fsp,
        config_key="123456",
        delivery_mechanism=fsp_config.delivery_mechanism,
        country=fsp_config.country,
        office=fsp_config.office,
    )
    pi = PaymentInstructionFactory.create(
        fsp=fsp_config.fsp,
        payload={"config_key": "123456"},
        country=fsp_config.country,
        office=fsp_config.office,
        delivery_mechanism=fsp_config.delivery_mechanism,
        export=export_template,
    )
    PaymentRecordFactory.create(parent=pi)
    return pi


@pytest.fixture
def serializer_update_setup(token_user):
    user, _ = token_user
    system = SystemFactory.create(owner=user)
    fsp = FinancialServiceProviderFactory.create()
    remote_id = "existing_remote_id"
    instruction = PaymentInstructionFactory.create(
        system=system, fsp=fsp, remote_id=remote_id, payload={"initial": "data"}
    )
    return {"system": system, "fsp": fsp, "remote_id": remote_id, "instruction": instruction}


@pytest.fixture
def office_country_setup(token_user):
    user, _ = token_user
    system = SystemFactory.create(owner=user)
    fsp = FinancialServiceProviderFactory.create()
    CountryFactory.create(iso_code2="US", iso_code3="USA", iso_num="840", name="USA")
    CountryFactory.create(iso_code2="FR", iso_code3="FRA", iso_num="250", name="France")
    OfficeFactory.create(code="supervised_office", supervised=True)
    return {"system": system, "fsp": fsp}


@pytest.fixture
def no_country_setup(token_user):
    user, _ = token_user
    system = SystemFactory.create(owner=user)
    fsp = FinancialServiceProviderFactory.create()
    return {"system": system, "fsp": fsp}


@pytest.fixture
def account_type_obj():
    return AccountTypeFactory.create(key="old_key", label="old_label")


@pytest.fixture
def delivery_mechanism_obj():
    return DeliveryMechanismFactory.create(code="DM_OLD", name="old")


@pytest.fixture
def fsp_obj():
    return FinancialServiceProviderFactory.create(name="old_name")


@pytest.fixture
def config_obj():
    return FinancialServiceProviderConfigFactory.create()


@pytest.fixture
def payment_record_message():
    return PaymentRecordFactory.create(message="old_msg")


@pytest.fixture
def export_template_obj():
    return ExportTemplateFactory.create(config_key="old_key")


@pytest.fixture
def corridor_obj():
    return CorridorFactory.create(description="old")


@pytest.fixture
def service_provider_code_obj():
    return ServiceProviderCodeFactory.create(description="old")


def _test_payment_instruction_create(api_client, token_user, mg, payload, system):
    user, token = token_user
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
    ("action", "detail", "status"),
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_instruction(api_client, action, detail, status, token_user, payment_record):
    user, token = token_user
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[payment_record.parent.remote_id])
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
def test_payment_instruction_actions(api_client, action, detail, status, token_user, payment_record):
    user, token = token_user
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[payment_record.parent.remote_id])
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
def test_payment_instruction_create(api_client, token_user, mg, payload, system):
    _test_payment_instruction_create(api_client, token_user, mg, payload, system)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"config_key": "tester_one", "destination_country": "ES"}',
    ],
)
def test_payment_instruction_create_with_office(api_client, token_user, mg, payload, supervised_office, system):
    _test_payment_instruction_create(api_client, token_user, mg, payload, system)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action", "detail", "status"),
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_record_list(api_client, action, detail, status, token_user, payment_record):
    user, token = token_user
    if detail:
        url = reverse(f"rest:payment-record-{action}", args=[payment_record.remote_id])
    else:
        url = reverse(f"rest:payment-record-{action}")
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token)
    assert view.status_code == status


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_payment_record_cancel(mock_refund, api_client, token_user, mg, payment_record):
    user, token = token_user
    url = reverse("rest:payment-record-cancel", args=[payment_record.remote_id])

    mock_refund.side_effect = None
    api_client.force_authenticate(user=user, token=token)
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token)

    assert view.status_code == 200


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_payment_record_cancel_fail(mock_refund, api_client, token_user, mg, payment_record):
    user, token = token_user
    url = reverse("rest:payment-record-cancel", args=[payment_record.remote_id])

    mock_refund.side_effect = TransitionNotAllowed("Cannot cancel this record")
    api_client.force_authenticate(user=user, token=token)
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token)

    assert view.status_code == 400


@pytest.mark.django_db
def test_instructions_add_records_ok(api_client, token_user, open_payment_record):
    user, token = token_user
    url = reverse("rest:payment-instruction-add-records", args=[open_payment_record.parent.remote_id])
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
    assert view.json()["remote_id"] == open_payment_record.parent.remote_id
    assert "adalberto" in view.json()["records"]


@pytest.mark.django_db
def test_instructions_add_records_ko(api_client, token_user, open_payment_record):
    user, token = token_user
    url = reverse("rest:payment-instruction-add-records", args=[open_payment_record.parent.remote_id])
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
    assert view.json()["remote_id"] == open_payment_record.parent.remote_id
    assert view.json()["errors"] == {
        "1": {"remote_id": ["This field may not be null."]},
        "2": {"record_code": ["This field may not be null."]},
    }


@pytest.mark.django_db
def test_instructions_add_records_invalid_status(api_client, token_user, aborted_payment_record):
    user, token = token_user
    url = reverse("rest:payment-instruction-add-records", args=[aborted_payment_record.parent.remote_id])
    api_client.force_authenticate(user=user, token=token)
    view = api_client.post(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == 400
    assert view.json()["message"] == "Cannot add records to a not Open Plan"
    assert view.json()["status"] == "ABORTED"


@pytest.mark.django_db
def test_payment_instruction_download_fail(api_client, token_user, download_fail_setup):
    user, token = token_user
    pr = download_fail_setup
    url = reverse("rest:payment-instruction-download", args=[pr.parent.remote_id])
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)

    assert view.status_code == 400
    assert view.data.get("status_error") == "No template found"
    assert pr.parent.jobs.count() == 0


@pytest.mark.django_db
def test_payment_instruction_download(api_client, token_user, download_setup):
    user, token = token_user
    pi = download_setup
    url = reverse("rest:payment-instruction-download", args=[pi.remote_id])
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == 202
    assert view.json()["message"] == "Export scheduled"
    job = pi.jobs.get()
    assert job.type == "STANDARD_TASK"
    assert job.owner == user
    assert job.config["payment_instruction_id"] == pi.pk
    assert job.config["send_to"] == user.email


@pytest.mark.django_db
def test_payment_instruction_download_requires_user_email(api_client, token_user, download_requires_email_setup):
    user, token = token_user
    pi = download_requires_email_setup
    url = reverse("rest:payment-instruction-download", args=[pi.remote_id])
    api_client.force_authenticate(user=user, token=token)
    view = api_client.get(url, user=user, HTTP_AUTHORIZATION=token, expect_errors=True)
    assert view.status_code == 400
    assert view.json()["status_error"] == "User email is required"
    assert pi.jobs.count() == 0


@pytest.mark.django_db
def test_health_check(api_client, token_user):
    url = "http://testserver/health"

    view = api_client.get(url)

    assert view.status_code == 200
    assert view.text == "OK"


@pytest.mark.django_db
def test_payment_instruction_serializer_update(api_client, token_user, serializer_update_setup):
    user, token = token_user
    system = serializer_update_setup["system"]
    fsp = serializer_update_setup["fsp"]
    remote_id = serializer_update_setup["remote_id"]
    instruction = serializer_update_setup["instruction"]

    url = reverse("rest:payment-instruction-list")
    data = {"remote_id": remote_id, "fsp": fsp.id, "payload": {"updated": "data"}, "external_code": "new_code"}

    api_client.force_authenticate(user=user, token=token)
    response = api_client.post(url, data=data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    instruction.refresh_from_db()
    assert instruction.payload == {"updated": "data"}
    assert instruction.external_code == "new_code"
    assert PaymentInstruction.objects.filter(remote_id=remote_id, system=system).count() == 1


@pytest.mark.django_db
def test_payment_instruction_perform_create_with_office_and_country(api_client, token_user, office_country_setup):
    user, token = token_user
    system = office_country_setup["system"]
    fsp = office_country_setup["fsp"]

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
def test_payment_instruction_perform_create_no_destination_country(api_client, token_user, no_country_setup):
    user, token = token_user
    system = no_country_setup["system"]
    fsp = no_country_setup["fsp"]

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


# ──────────────────────────────────────────────
# PATCH (partial_update) tests
# ──────────────────────────────────────────────


@pytest.mark.django_db
def test_account_type_patch(api_client, token_user, account_type_obj):
    user, token = token_user
    url = reverse("rest:account-type-detail", args=[account_type_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"label": "new_label"}, format="json")
    assert resp.status_code == 200
    account_type_obj.refresh_from_db()
    assert account_type_obj.label == "new_label"
    assert account_type_obj.key == "old_key"


@pytest.mark.django_db
def test_delivery_mechanism_patch(api_client, token_user, delivery_mechanism_obj):
    user, token = token_user
    url = reverse("rest:delivery-mechanism-detail", args=[delivery_mechanism_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"name": "new"}, format="json")
    assert resp.status_code == 200
    delivery_mechanism_obj.refresh_from_db()
    assert delivery_mechanism_obj.name == "new"


@pytest.mark.django_db
def test_fsp_patch(api_client, token_user, fsp_obj):
    user, token = token_user
    url = reverse("rest:fsp-detail", args=[fsp_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"name": "new_name"}, format="json")
    assert resp.status_code == 200
    fsp_obj.refresh_from_db()
    assert fsp_obj.name == "new_name"


@pytest.mark.django_db
def test_configuration_patch(api_client, token_user, config_obj):
    user, token = token_user
    url = reverse("rest:config-detail", args=[config_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"label": "updated_label"}, format="json")
    assert resp.status_code == 200
    config_obj.refresh_from_db()
    assert config_obj.label == "updated_label"


@pytest.mark.django_db
def test_payment_instruction_patch(api_client, token_user, payment_record):
    user, token = token_user
    pi = payment_record.parent
    url = reverse("rest:payment-instruction-detail", args=[pi.remote_id])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"active": False}, format="json")
    assert resp.status_code == 200
    pi.refresh_from_db()
    assert pi.active is False


@pytest.mark.django_db
def test_payment_record_patch(api_client, token_user, payment_record_message):
    user, token = token_user
    url = reverse("rest:payment-record-detail", args=[payment_record_message.remote_id])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"message": "new_msg"}, format="json")
    assert resp.status_code == 200
    payment_record_message.refresh_from_db()
    assert payment_record_message.message == "new_msg"


@pytest.mark.django_db
def test_export_template_patch(api_client, token_user, export_template_obj):
    user, token = token_user
    url = reverse("rest:export-template-detail", args=[export_template_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"config_key": "new_key"}, format="json")
    assert resp.status_code == 200
    export_template_obj.refresh_from_db()
    assert export_template_obj.config_key == "new_key"


@pytest.mark.django_db
def test_corridor_patch(api_client, token_user, corridor_obj):
    user, token = token_user
    url = reverse("rest:wu-corridor-detail", args=[corridor_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"description": "new"}, format="json")
    assert resp.status_code == 200
    corridor_obj.refresh_from_db()
    assert corridor_obj.description == "new"


@pytest.mark.django_db
def test_service_provider_code_patch(api_client, token_user, service_provider_code_obj):
    user, token = token_user
    url = reverse("rest:wu-service-provider-code-detail", args=[service_provider_code_obj.pk])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"description": "new"}, format="json")
    assert resp.status_code == 200
    service_provider_code_obj.refresh_from_db()
    assert service_provider_code_obj.description == "new"


@pytest.mark.django_db
def test_payment_instruction_patch_validation_error(api_client, token_user, payment_record):
    user, token = token_user
    pi = payment_record.parent
    url = reverse("rest:payment-instruction-detail", args=[pi.remote_id])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"fsp": -999}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_payment_record_patch_validation_error(api_client, token_user, payment_record):
    user, token = token_user
    url = reverse("rest:payment-record-detail", args=[payment_record.remote_id])
    api_client.force_authenticate(user=user, token=token)
    resp = api_client.patch(url, {"parent": "nonexistent"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_add_records_list_error_branch(api_client, token_user, open_payment_record):
    user, token = token_user
    url = reverse("rest:payment-instruction-add-records", args=[open_payment_record.parent.remote_id])
    payload = [
        {
            "record_code": "valid",
            "remote_id": "valid",
            "payload": {"key": "value"},
        },
        {
            "record_code": None,
            "remote_id": "also_valid",
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
    errors = view.json()["errors"]
    assert "1" in errors
    assert "record_code" in errors["1"]
