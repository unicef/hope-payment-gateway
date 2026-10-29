from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from factories import (
    APITokenFactory,
    CorridorFactory,
    FinancialServiceProviderFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    ServiceProviderCodeFactory,
    SuperUserFactory,
)
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState


def authenticate(api_client, token_user):
    user, token = token_user
    api_client.force_authenticate(user=user, token=token)
    return api_client


@pytest.mark.django_db
def test_read_only_token_can_read_payment_instructions(api_client, read_only_token_user):
    PaymentInstructionFactory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.get(reverse("rest:payment-instruction-list"))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_read_only_token_cannot_create_payment_instruction(api_client, read_only_token_user):
    fsp = FinancialServiceProviderFactory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.post(
        reverse("rest:payment-instruction-list"),
        {"remote_id": "read-only-create", "external_code": "read-only-create", "fsp": fsp.pk, "payload": {}},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_read_only_token_cannot_patch_payment_instruction(api_client, read_only_token_user):
    instruction = PaymentInstructionFactory.create(active=True)
    authenticate(api_client, read_only_token_user)

    response = api_client.patch(
        reverse("rest:payment-instruction-detail", args=[instruction.remote_id]),
        {"active": False},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    instruction.refresh_from_db()
    assert instruction.active is True


@pytest.mark.django_db
def test_read_only_token_cannot_drive_payment_instruction_state_machine(api_client, read_only_token_user):
    instruction = PaymentInstructionFactory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.post(reverse("rest:payment-instruction-open", args=[instruction.remote_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_read_only_token_cannot_cancel_payment_record(mock_refund, api_client, read_only_token_user):
    record = PaymentRecordFactory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.post(reverse("rest:payment-record-cancel", args=[record.remote_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_refund.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url_name", "factory"),
    [
        ("rest:wu-corridor-detail", CorridorFactory),
        ("rest:wu-service-provider-code-detail", ServiceProviderCodeFactory),
    ],
)
def test_read_only_token_cannot_write_western_union_routing_data(api_client, read_only_token_user, url_name, factory):
    instance = factory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.patch(
        reverse(url_name, args=[instance.pk]),
        {"description": "forbidden"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_token_without_grants_cannot_read_western_union_routing_data(api_client, no_grant_token_user):
    CorridorFactory.create()
    authenticate(api_client, no_grant_token_user)

    response = api_client.get(reverse("rest:wu-corridor-list"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_plan_manage_token_can_drive_payment_instruction_state_machine(api_client, plan_manage_token_user):
    instruction = PaymentInstructionFactory.create()
    authenticate(api_client, plan_manage_token_user)

    response = api_client.post(reverse("rest:payment-instruction-open", args=[instruction.remote_id]))

    assert response.status_code == status.HTTP_200_OK
    instruction.refresh_from_db()
    assert instruction.status == "OPEN"


@pytest.mark.django_db
def test_plan_upload_token_can_add_payment_records(api_client, plan_upload_token_user):
    instruction = PaymentInstructionFactory.create(status=PaymentInstructionState.OPEN)
    authenticate(api_client, plan_upload_token_user)

    response = api_client.post(
        reverse("rest:payment-instruction-add-records", args=[instruction.remote_id]),
        [{"record_code": "uploaded", "remote_id": "uploaded", "payload": {"key": "value"}}],
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert "uploaded" in response.json()["records"]


@pytest.mark.django_db
def test_plan_upload_token_cannot_patch_payment_instruction(api_client, plan_upload_token_user):
    instruction = PaymentInstructionFactory.create(active=True)
    authenticate(api_client, plan_upload_token_user)

    response = api_client.patch(
        reverse("rest:payment-instruction-detail", args=[instruction.remote_id]),
        {"active": False},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    instruction.refresh_from_db()
    assert instruction.active is True


@pytest.mark.django_db
def test_plan_upload_token_cannot_drive_payment_instruction_state_machine(api_client, plan_upload_token_user):
    instruction = PaymentInstructionFactory.create()
    authenticate(api_client, plan_upload_token_user)

    response = api_client.post(reverse("rest:payment-instruction-open", args=[instruction.remote_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.client.WesternUnionClient.refund")
def test_plan_upload_token_cannot_cancel_payment_record(mock_refund, api_client, plan_upload_token_user):
    record = PaymentRecordFactory.create()
    authenticate(api_client, plan_upload_token_user)

    response = api_client.post(reverse("rest:payment-record-cancel", args=[record.remote_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_refund.assert_not_called()


@pytest.mark.django_db
def test_read_only_token_cannot_delete_western_union_routing_data(api_client, read_only_token_user):
    corridor = CorridorFactory.create()
    authenticate(api_client, read_only_token_user)

    response = api_client.delete(reverse("rest:wu-corridor-detail", args=[corridor.pk]))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert CorridorFactory._meta.model.objects.filter(pk=corridor.pk).exists()


@pytest.mark.django_db
def test_superuser_is_not_bound_by_token_grants(api_client):
    user = SuperUserFactory.create()
    token = APITokenFactory.create(user=user, grants=[])
    PaymentInstructionFactory.create()
    api_client.force_authenticate(user=user, token=token)

    response = api_client.get(reverse("rest:payment-instruction-list"))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_plan_manage_token_can_patch_western_union_routing_data(api_client, plan_manage_token_user):
    corridor = CorridorFactory.create()
    authenticate(api_client, plan_manage_token_user)

    response = api_client.patch(
        reverse("rest:wu-corridor-detail", args=[corridor.pk]),
        {"description": "managed"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    corridor.refresh_from_db()
    assert corridor.description == "managed"
