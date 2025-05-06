import pytest
from django.urls import reverse
from django.test import RequestFactory
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
from hope_payment_gateway.apps.fsp.moneygram.client import InvalidTokenError


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def user_with_permissions(user):
    permission = Permission.objects.get(codename="can_create_transaction", content_type__app_label="moneygram")
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def payment_record(mg):
    instruction = PaymentInstructionFactory(fsp=mg)
    return PaymentRecordFactory(parent=instruction)


@pytest.fixture
def req(user):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    return request


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
def test_handle_mg_response_success(
    mock_client, user_with_permissions, payment_record_admin_instance, payment_record, req
):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.return_value = (
        {"test": "request"},
        mock_resp,
        "/disbursement/v1/transactions",
    )

    response = payment_record_admin_instance.handle_mg_response(
        req,
        payment_record.pk,
        "create_transaction",
        "Create Transaction",
    )

    assert response.status_code == 200
    assert response.context_data["title"] == "Create Transaction"
    assert response.context_data["code"] == 200
    assert response.context_data["url"] == "/disbursement/v1/transactions"
    assert response.context_data["request_format"] == "json"
    assert response.context_data["response_format"] == "json"
    assert response.context_data["content_request"] == {"test": "request"}
    assert response.context_data["content_response"] == {"test": "response"}


handle_error_mock_data = {"error": "Something went wrong"}


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
@patch("hope_payment_gateway.apps.gateway.admin.base.PaymentRecordAdmin.handle_error")
def test_handle_mg_response_status_code_300(
    handle_error_data, mock_client, user_with_permissions, payment_record_admin_instance, payment_record, client
):
    mock_resp = MagicMock()
    mock_resp.status_code = 300
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.return_value = (
        {"test": "request"},
        mock_resp,
        "/disbursement/v1/transactions",
    )

    handle_error_data.return_value = (messages.ERROR, ["Something went wrong"])

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_mg_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "Something went wrong"


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
def test_handle_mg_response_no_response(
    mock_client, user_with_permissions, payment_record_admin_instance, payment_record, client
):
    mock_resp = MagicMock()
    mock_resp.status_code = 300
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.return_value = (
        {"test": "request"},
        None,
        "/disbursement/v1/transactions",
    )

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_mg_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "Connection Error"


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
def test_handle_mg_response_keyerror(
    mock_client, user_with_permissions, payment_record_admin_instance, payment_record, client
):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.side_effect = KeyError("some field not found")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_mg_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "Keyerror: 'some field not found'"


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
def test_handle_mg_response_transition_not_allowed(
    mock_client, user_with_permissions, payment_record_admin_instance, payment_record, client
):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.side_effect = TransitionNotAllowed("transition_not_allowed")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_mg_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert "transition_not_allowed" in str(user_messages[0])


@pytest.mark.django_db
@patch("hope_payment_gateway.apps.gateway.admin.moneygram.MoneyGramClient")
def test_handle_mg_response_invalid_token_error(
    mock_client, user_with_permissions, payment_record_admin_instance, payment_record, client
):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.data = {"test": "response"}

    mock_client.return_value.create_transaction.side_effect = InvalidTokenError("invalid token")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_mg_create_transaction", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
    assert str(user_messages[0]) == "invalid token"
