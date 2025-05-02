import pytest
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from constance.test import override_config
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
    CorridorFactory,
)


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def western_union_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def user_with_permissions(user):
    permission = Permission.objects.get(codename="can_prepare_transaction", content_type__app_label="western_union")
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def payment_record(wu):
    instruction = PaymentInstructionFactory(fsp=wu)
    return PaymentRecordFactory(parent=instruction)


@pytest.mark.django_db
def test_wu_prepare_payload_no_permissions(user, western_union_admin_instance, payment_record):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
        "delivery_mechanism": "CASH",
    }

    with pytest.raises(PermissionDenied):
        western_union_admin_instance.wu_prepare_payload(western_union_admin_instance, request, payment_record.pk)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_prepare_payload_success(user_with_permissions, western_union_admin_instance, payment_record, client):
    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
        "delivery_mechanism": "CASH",
        "first_name": "John",
        "last_name": "Doe",
        "amount": 100,
    }
    payment_record.save()
    CorridorFactory(destination_country="US", destination_currency="USD")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_prepare_payload", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert "content_request" in response.context_data
    assert "content_response" in response.context_data
    assert response.context_data["title"] == "Western Union Payload"


def assert_error_redirect(response, payment_record):
    assert response.status_code == 302
    assert response.url == reverse("admin:gateway_paymentrecord_change", args=[payment_record.pk])
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_prepare_payload_payload_exception(
    user_with_permissions, western_union_admin_instance, payment_record, client
):
    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_prepare_payload", args=[payment_record.pk])
    response = client.get(url)
    assert_error_redirect(response, payment_record)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_prepare_payload_invalid_corridor(
    user_with_permissions, western_union_admin_instance, payment_record, client
):
    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
        "delivery_mechanism": "CASH",
        "first_name": "John",
        "last_name": "Doe",
        "amount": 100,
    }
    payment_record.save()
    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_prepare_payload", args=[payment_record.pk])
    response = client.get(url)

    assert_error_redirect(response, payment_record)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_prepare_payload_missing_key(user_with_permissions, western_union_admin_instance, payment_record, client):
    payment_record.payload = {
        "delivery_services_code": "800",
    }

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_prepare_payload", args=[payment_record.pk])
    response = client.get(url)

    assert_error_redirect(response, payment_record)
