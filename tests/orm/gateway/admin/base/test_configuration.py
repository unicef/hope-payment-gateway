import pytest
from django.urls import reverse
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from hope_payment_gateway.apps.gateway.admin.base import PaymentRecordAdmin, PaymentInstructionAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentInstruction
from tests.factories.payment import (
    FinancialServiceProviderFactory,
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    CountryFactory,
    OfficeFactory,
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


@pytest.mark.django_db
def test_payment_record_configuration_view_redirects_correctly(
    user, payment_record_admin_instance, request_with_messages
):
    request = request_with_messages
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    country = CountryFactory()
    office = OfficeFactory()

    config = FinancialServiceProviderConfigFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    instruction = PaymentInstructionFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    payment_record = PaymentRecordFactory(parent=instruction)

    response = payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


@pytest.mark.django_db
def test_payment_record_configuration_view_handles_missing_config(
    user, payment_record_admin_instance, request_with_messages
):
    request = request_with_messages
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    country = CountryFactory()

    instruction = PaymentInstructionFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
    )

    payment_record = PaymentRecordFactory(parent=instruction)

    response = payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)

    assert response.url == reverse("admin:gateway_paymentrecord_change", args=[payment_record.pk])


@pytest.mark.django_db
def test_payment_instruction_configuration_view_redirects_correctly(
    user, payment_instruction_admin_instance, request_with_messages
):
    request = request_with_messages
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    country = CountryFactory()
    office = OfficeFactory()

    config = FinancialServiceProviderConfigFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    instruction = PaymentInstructionFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
        office=office,
    )

    response = payment_instruction_admin_instance.configuration(
        payment_instruction_admin_instance, request, instruction.pk
    )

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


@pytest.mark.django_db
def test_payment_instruction_configuration_view_handles_missing_config(
    user, payment_instruction_admin_instance, request_with_messages
):
    request = request_with_messages
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    country = CountryFactory()

    instruction = PaymentInstructionFactory(
        fsp=fsp,
        delivery_mechanism=delivery_mechanism,
        country=country,
    )

    response = payment_instruction_admin_instance.configuration(
        payment_instruction_admin_instance, request, instruction.pk
    )

    assert response.url == reverse("admin:gateway_paymentinstruction_change", args=[instruction.pk])
