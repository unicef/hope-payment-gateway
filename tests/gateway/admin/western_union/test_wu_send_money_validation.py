import pytest
from django.urls import reverse
from django.test import RequestFactory
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
    CorridorFactory,
)
from tests.gateway.admin.western_union import assert_error_redirect


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
def test_wu_send_money_validation_no_permissions(user, western_union_admin_instance, payment_record):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    with pytest.raises(PermissionDenied):
        western_union_admin_instance.wu_send_money_validation(western_union_admin_instance, request, payment_record.pk)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_send_money_validation_success(user_with_permissions, western_union_admin_instance, payment_record, client):
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
    url = reverse("admin:gateway_paymentrecord_wu_send_money_validation", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert "content_request" in response.context_data
    assert "content_response" in response.context_data
    assert response.context_data["msg"] == "First call: check if data is valid \n it returns MTCN"


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_send_money_validation_payload_exception(
    user_with_permissions, western_union_admin_instance, payment_record, client
):
    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentrecord_wu_send_money_validation", args=[payment_record.pk])
    response = client.get(url)
    assert_error_redirect(response, payment_record)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_send_money_validation_invalid_corridor(
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
    url = reverse("admin:gateway_paymentrecord_wu_send_money_validation", args=[payment_record.pk])
    response = client.get(url)

    assert_error_redirect(response, payment_record)
