from unittest.mock import Mock

import pytest
from django.urls import reverse
from django.test import RequestFactory
from django.contrib import messages
from django.contrib.admin.sites import AdminSite

from hope_api_auth.auth import User
from hope_payment_gateway.apps.gateway.admin.base import PaymentRecordAdmin, ImportCSVForm, PaymentInstructionAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentInstruction
from tests.factories.payment import (
    FinancialServiceProviderFactory,
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


def test_handle_error_500(payment_record_admin_instance):
    resp = Mock()
    resp.status_code = 500
    resp.data = {"error": "Something went wrong"}
    expected_message = ["Something went wrong"]
    expected_loglevel = messages.ERROR
    loglevel, msgs = payment_record_admin_instance.handle_error(resp)
    assert loglevel == expected_loglevel
    assert msgs == expected_message


def test_handle_error_400(payment_record_admin_instance):
    resp = Mock()
    resp.status_code = 400
    resp.data = {"error": "Something went wrong"}
    expected_message = ["Something went wrong"]
    expected_loglevel = messages.WARNING
    loglevel, msgs = payment_record_admin_instance.handle_error(resp)
    assert loglevel == expected_loglevel
    assert msgs == expected_message


@pytest.mark.django_db
def test_configuration_view_redirects_correctly(user, payment_record_admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    config = FinancialServiceProviderConfigFactory(key="test_config", fsp=fsp, delivery_mechanism=delivery_mechanism)

    instruction = PaymentInstructionFactory(fsp=fsp, extra={"config_key": "test_config"})

    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})

    response = payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


@pytest.mark.django_db
def test_configuration_view_handles_missing_config(user, payment_record_admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    fsp = FinancialServiceProviderFactory()
    instruction = PaymentInstructionFactory(fsp=fsp, extra={"config_key": "non_existent_config"})

    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})

    with pytest.raises(FinancialServiceProviderConfigFactory._meta.model.DoesNotExist):
        payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)


@pytest.fixture
def payment_instruction_admin_instance(admin_site) -> PaymentInstructionAdmin:
    return PaymentInstructionAdmin(PaymentInstruction, admin_site)


@pytest.fixture
def user_with_permissions(user) -> User:
    permission = Permission.objects.get(codename="can_import_records", content_type__app_label="gateway")
    user.user_permissions.add(permission)
    return user


@pytest.mark.django_db
def test_import_records_get_request(user_with_permissions, payment_instruction_admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user_with_permissions

    payment_instruction = PaymentInstructionFactory()

    response = payment_instruction_admin_instance.import_records(
        payment_instruction_admin_instance, request, payment_instruction.pk
    )

    assert response.status_code == 200
    assert "form" in response.context_data
    assert isinstance(response.context_data["form"], ImportCSVForm)


@pytest.mark.django_db
def test_import_records_no_permissions(user, payment_instruction_admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    payment_instruction = PaymentInstructionFactory()

    with pytest.raises(PermissionDenied):
        payment_instruction_admin_instance.import_records(
            payment_instruction_admin_instance, request, payment_instruction.pk
        )


@pytest.mark.django_db
def test_import_records_valid_csv(user_with_permissions, payment_instruction_admin_instance, client):
    instruction = PaymentInstructionFactory()

    csv_content = "record_code,first_name,last_name,amount,phone_no,service_provider_code\n"
    csv_content += "TEST001,John,Doe,100,1234567890,SP001\n"
    csv_content += "TEST002,Jane,Smith,200,0987654321,SP002\n"

    csv_file = SimpleUploadedFile("test.csv", csv_content.encode("utf-8-sig"), content_type="text/csv")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentinstruction_import_records", args=[instruction.pk])
    response = client.post(url, {"file": csv_file})

    records = PaymentRecord.objects.filter(parent=instruction)
    assert records.count() == 2
    assert records.filter(record_code="TEST001").exists()
    assert records.filter(record_code="TEST002").exists()

    assert response.status_code == 302
    assert response.url == reverse("admin:gateway_paymentinstruction_change", args=[instruction.pk])

    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert "Uploaded 2 records" in str(user_messages[0])


@pytest.mark.django_db
def test_import_records_duplicates(user_with_permissions, payment_instruction_admin_instance, client):
    instruction = PaymentInstructionFactory()

    csv_content = "record_code,first_name,last_name,amount,phone_no,service_provider_code\n"
    csv_content += "TEST001,John,Doe,100,1234567890,SP001\n"
    csv_content += "TEST001,Jane,Smith,200,0987654321,SP002\n"

    csv_file = SimpleUploadedFile("test.csv", csv_content.encode("utf-8-sig"), content_type="text/csv")

    client.force_login(user_with_permissions)
    url = reverse("admin:gateway_paymentinstruction_import_records", args=[instruction.pk])
    response = client.post(url, {"file": csv_file})

    assert response.status_code == 200
    assert "form" in response.context_data
    assert isinstance(response.context_data["form"], ImportCSVForm)

    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR
