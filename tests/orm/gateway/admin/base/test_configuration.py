import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

from hope_payment_gateway.apps.gateway.admin.base import PaymentInstructionAdmin, PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentInstruction, PaymentRecord
from tests.factories.payment import (
    CountryFactory,
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    FinancialServiceProviderFactory,
    OfficeFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def request_with_messages(request_factory):
    request = request_factory.get("/")
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    middleware = MessageMiddleware(lambda r: None)
    middleware.process_request(request)
    return request


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def payment_instruction_admin_instance(admin_site) -> PaymentInstructionAdmin:
    return PaymentInstructionAdmin(PaymentInstruction, admin_site)


# ---------- test_payment_record_configuration_view_redirects_correctly ----------


@pytest.fixture
def pr_redirect_data():
    fsp = FinancialServiceProviderFactory.create()
    delivery_mechanism = DeliveryMechanismFactory.create(code="CASH")
    country = CountryFactory.create()
    office = OfficeFactory.create()

    config = FinancialServiceProviderConfigFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    instruction = PaymentInstructionFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    payment_record = PaymentRecordFactory.create(parent=instruction)
    return config, payment_record


@pytest.mark.django_db
def test_payment_record_configuration_view_redirects_correctly(
    user, payment_record_admin_instance, request_with_messages, pr_redirect_data
):
    request = request_with_messages
    request.user = user

    config, payment_record = pr_redirect_data

    response = payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


# ---------- test_payment_record_configuration_view_handles_missing_config ----------


@pytest.fixture
def pr_missing_record():
    fsp = FinancialServiceProviderFactory.create()
    delivery_mechanism = DeliveryMechanismFactory.create(code="CASH")
    country = CountryFactory.create()

    instruction = PaymentInstructionFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
    )

    return PaymentRecordFactory.create(parent=instruction)


@pytest.mark.django_db
def test_payment_record_configuration_view_handles_missing_config(
    user, payment_record_admin_instance, request_with_messages, pr_missing_record
):
    request = request_with_messages
    request.user = user

    response = payment_record_admin_instance.configuration(payment_record_admin_instance, request, pr_missing_record.pk)

    assert response.url == reverse("admin:gateway_paymentrecord_change", args=[pr_missing_record.pk])


# ---------- test_payment_instruction_configuration_view_redirects_correctly ----------


@pytest.fixture
def pi_redirect_data():
    fsp = FinancialServiceProviderFactory.create()
    delivery_mechanism = DeliveryMechanismFactory.create(code="CASH")
    country = CountryFactory.create()
    office = OfficeFactory.create()

    config = FinancialServiceProviderConfigFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    instruction = PaymentInstructionFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    return config, instruction


@pytest.mark.django_db
def test_payment_instruction_configuration_view_redirects_correctly(
    user, payment_instruction_admin_instance, request_with_messages, pi_redirect_data
):
    request = request_with_messages
    request.user = user

    config, instruction = pi_redirect_data

    response = payment_instruction_admin_instance.configuration(
        payment_instruction_admin_instance, request, instruction.pk
    )

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


# ---------- test_payment_instruction_configuration_view_handles_missing_config ----------


@pytest.fixture
def pi_missing_instruction():
    fsp = FinancialServiceProviderFactory.create()
    delivery_mechanism = DeliveryMechanismFactory.create(code="CASH")
    country = CountryFactory.create()

    return PaymentInstructionFactory.create(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
    )


@pytest.mark.django_db
def test_payment_instruction_configuration_view_handles_missing_config(
    user, payment_instruction_admin_instance, request_with_messages, pi_missing_instruction
):
    request = request_with_messages
    request.user = user

    response = payment_instruction_admin_instance.configuration(
        payment_instruction_admin_instance, request, pi_missing_instruction.pk
    )

    assert response.url == reverse("admin:gateway_paymentinstruction_change", args=[pi_missing_instruction.pk])
