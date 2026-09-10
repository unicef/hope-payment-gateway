import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission
from unittest.mock import patch

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def payment_record(palpay):
    instruction = PaymentInstructionFactory.create(fsp=palpay)
    return PaymentRecordFactory.create(parent=instruction)


@pytest.mark.parametrize(
    ("method", "title", "permission", "path"),
    [
        ("get_profile", "Check Profile", "can_check_profile", "pal_profile"),
        ("balance", "Check Balance", "can_check_balance", "pal_balance"),
        ("beneficiary", "Check Beneficiary", "can_check_beneficiary", "pal_beneficiary"),
        ("transactions", "Check Transactions", "can_check_transactions", "pal_transactions"),
        ("create_transaction", "Create Transaction", "can_create_transaction", "pal_create_transaction"),
        ("status", "Check Status", "can_check_status", "pal_status"),
        ("status_update", "Update Status", "can_update_status", "pal_status_update"),
    ],
)
@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.palpay.PalPayAdminMixin.handle_pal_response")
def test_handle_pal_response_called_correctly(
    mocked_handle_pal_response,
    payment_record_admin_instance,
    payment_record,
    client,
    user,
    method,
    title,
    permission,
    path,
):
    permission = Permission.objects.get(codename=permission, content_type__app_label="palpay")
    user.user_permissions.add(permission)

    client.force_login(user)
    url = reverse(f"admin:gateway_paymentrecord_{path}", args=[payment_record.pk])
    response = client.get(url)

    mocked_handle_pal_response.assert_called_once_with(
        response.wsgi_request,
        str(payment_record.pk),
        method,
        title,
    )


@pytest.mark.parametrize(
    ("permission", "path"),
    [
        ("can_check_profile", "pal_profile"),
        ("can_check_balance", "pal_balance"),
        ("can_check_beneficiary", "pal_beneficiary"),
        ("can_check_transactions", "pal_transactions"),
        ("can_create_transaction", "pal_create_transaction"),
        ("can_check_status", "pal_status"),
        ("can_update_status", "pal_status_update"),
    ],
)
@pytest.mark.django_db
def test_no_permissions(payment_record_admin_instance, payment_record, client, user, permission, path):
    client.force_login(user)
    url = reverse(f"admin:gateway_paymentrecord_{path}", args=[payment_record.pk])
    response = client.get(url)
    assert response.status_code == 403
