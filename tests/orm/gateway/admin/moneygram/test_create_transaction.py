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
def payment_record(mg):
    instruction = PaymentInstructionFactory(fsp=mg)
    return PaymentRecordFactory(parent=instruction)


@pytest.mark.parametrize(
    ("method", "title", "permission", "path"),
    [
        ("create_transaction", "Create Transaction", "can_create_transaction", "mg_create_transaction"),
        ("quote", "Quote", "can_quote_transaction", "mg_quote_transaction"),
        ("status", "Status", "can_check_status", "mg_status"),
        ("status_update", "Status Upload", "can_update_status", "mg_status_update"),
        ("get_required_fields", "Required Fields", "can_quote_transaction", "mg_get_required_fields"),
        ("get_service_options", "Service Options", "can_quote_transaction", "mg_get_service_options"),
        ("refund", "Refund", "can_cancel_transaction", "mg_refund"),
    ],
)
@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramAdminMixin.handle_mg_response")
def test_handle_mg_response_called_correctly(
    mocked_handle_mg_response,
    payment_record_admin_instance,
    payment_record,
    client,
    user,
    method,
    title,
    permission,
    path,
):
    permission = Permission.objects.get(codename=permission, content_type__app_label="moneygram")
    user.user_permissions.add(permission)

    client.force_login(user)
    url = reverse(f"admin:gateway_paymentrecord_{path}", args=[payment_record.pk])
    response = client.get(url)

    mocked_handle_mg_response.assert_called_once_with(
        response.wsgi_request,
        str(payment_record.pk),
        method,
        title,
    )


@pytest.mark.parametrize(
    ("permission", "path"),
    [
        ("can_create_transaction", "mg_create_transaction"),
        ("can_quote_transaction", "mg_quote_transaction"),
        ("can_check_status", "mg_status"),
        ("can_update_status", "mg_status_update"),
        ("can_quote_transaction", "mg_get_required_fields"),
        ("can_quote_transaction", "mg_get_service_options"),
        ("can_cancel_transaction", "mg_refund"),
    ],
)
@pytest.mark.django_db
def test_no_permissions(payment_record_admin_instance, payment_record, client, user, permission, path):
    client.force_login(user)
    url = reverse(f"admin:gateway_paymentrecord_{path}", args=[payment_record.pk])
    response = client.get(url)
    assert response.status_code == 403
