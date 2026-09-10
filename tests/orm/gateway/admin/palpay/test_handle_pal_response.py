import pytest
from django.urls import reverse
from constance.test import override_config
from django.contrib.auth.models import Permission
from unittest.mock import patch, MagicMock

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
)

from django.contrib import messages
from viewflow.fsm import TransitionNotAllowed


@pytest.fixture
def palpay_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def user_with_permissions(user):
    permission = Permission.objects.get(codename="can_create_transaction", content_type__app_label="palpay")
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def payment_record(palpay):
    instruction = PaymentInstructionFactory.create(fsp=palpay)
    return PaymentRecordFactory.create(parent=instruction)


@pytest.fixture
def req(user):
    from django.test import RequestFactory

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    return request


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.gateway.admin.palpay.PalPayClient")
def test_handle_pal_response_success(mock_client, user_with_permissions, palpay_admin_instance, payment_record, req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.return_value = (
        {"test": "request"},
        mock_resp,
        "/api/v1/moneytransfer/transfer/TEST001",
    )

    response = palpay_admin_instance.handle_pal_response(
        req,
        payment_record.pk,
        "create_transaction",
        "Create Transaction",
    )

    assert response.status_code == 200
    assert response.context_data["title"] == "Create Transaction"
    assert response.context_data["code"] == 200
    assert response.context_data["url"] == "/api/v1/moneytransfer/transfer/TEST001"
    assert response.context_data["request_format"] == "json"
    assert response.context_data["response_format"] == "json"
    assert response.context_data["content_request"] == {"test": "request"}
    assert response.context_data["content_response"] == {"test": "response"}


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.gateway.admin.palpay.PalPayClient")
def test_handle_pal_response_no_response(
    mock_client, user_with_permissions, palpay_admin_instance, payment_record, client
):
    mock_client.return_value.create_transaction.return_value = (
        {"test": "request"},
        None,
        "/api/v1/moneytransfer/transfer/TEST001",
    )

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_pal_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "Connection Error"


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.gateway.admin.palpay.PalPayClient")
def test_handle_pal_response_keyerror(
    mock_client, user_with_permissions, palpay_admin_instance, payment_record, client
):
    mock_client.return_value.create_transaction.side_effect = KeyError("some field not found")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_pal_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "'some field not found'"


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
@patch("hope_payment_gateway.apps.gateway.admin.palpay.PalPayClient")
def test_handle_pal_response_transition_not_allowed(
    mock_client, user_with_permissions, palpay_admin_instance, payment_record, client
):
    mock_client.return_value.create_transaction.side_effect = TransitionNotAllowed("transition_not_allowed")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_pal_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert "transition_not_allowed" in str(user_messages[0])
