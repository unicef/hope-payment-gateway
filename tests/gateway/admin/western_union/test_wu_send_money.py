import pytest
from django.urls import reverse
from django.test import RequestFactory
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from unittest.mock import patch

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
)
from tests.gateway.admin.western_union import assert_error_redirect


@pytest.fixture
def western_union_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def user_with_permissions(user):
    permission = Permission.objects.get(codename="can_create_transaction", content_type__app_label="western_union")
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def payment_record(wu):
    instruction = PaymentInstructionFactory(fsp=wu)
    return PaymentRecordFactory(parent=instruction)


@pytest.mark.django_db
def test_wu_send_money_no_permissions(user, western_union_admin_instance, payment_record):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    with pytest.raises(PermissionDenied):
        western_union_admin_instance.wu_send_money(western_union_admin_instance, request, payment_record.pk)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.gateway.admin.western_union.WesternUnionClient")
def test_wu_send_money_success(
    mock_wu_client, user_with_permissions, western_union_admin_instance, payment_record, client
):
    mock_response = {"title": "mocked title", "code": 200}
    mock_wu_client.return_value.create_transaction.return_value = mock_response

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_send_money", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert response.context_data["title"] == "mocked title"
    assert response.context_data["code"] == 200


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.gateway.admin.western_union.WesternUnionClient")
def test_wu_send_money_payment_record_not_found(
    mock_wu_client, user_with_permissions, western_union_admin_instance, payment_record, client
):
    mock_wu_client.return_value.create_transaction.side_effect = PaymentRecord.DoesNotExist
    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_send_money", args=[payment_record.pk])  # Non-existent ID
    response = client.get(url)
    assert_error_redirect(response, payment_record)
