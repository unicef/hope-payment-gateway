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


@pytest.fixture
def western_union_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def user_with_permissions(user):
    permission = Permission.objects.get(codename="can_update_status", content_type__app_label="western_union")
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def payment_record(wu):
    instruction = PaymentInstructionFactory(fsp=wu)
    return PaymentRecordFactory(parent=instruction)


@pytest.mark.django_db
def test_wu_status_update_no_permissions(user, western_union_admin_instance, payment_record):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    with pytest.raises(PermissionDenied):
        western_union_admin_instance.wu_status_update(western_union_admin_instance, request, payment_record.pk)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.gateway.admin.western_union.WesternUnionClient")
def test_wu_status_update_success(
    mock_wu_client, user_with_permissions, western_union_admin_instance, payment_record, client
):
    mock_response = {
        "title": "mocked title",
    }
    mock_wu_client.return_value.status.return_value = mock_response

    payment_record.auth_code = "1234567890"
    payment_record.save()

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_status_update", args=[payment_record.pk])
    response = client.get(url)

    mock_wu_client.return_value.status.assert_called_once_with(payment_record.fsp_code, True)
    assert response.status_code == 200
    assert response.context_data["title"] == "mocked title"
    assert "msg" in response.context_data
    assert "1234567890" in response.context_data["msg"]


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_status_update_missing_mtcn(user_with_permissions, western_union_admin_instance, payment_record, client):
    payment_record.auth_code = None
    payment_record.save()

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_status_update", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert "msg" not in response.context_data
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert str(user_messages[0]) == "Missing MTCN"
