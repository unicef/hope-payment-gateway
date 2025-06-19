import pytest
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from hope_payment_gateway.apps.gateway.admin.base import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    FinancialServiceProviderFactory,
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.mark.django_db
def test_configuration_view_redirects_correctly(user, payment_record_admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    config = FinancialServiceProviderConfigFactory(key="test_config", fsp=fsp, delivery_mechanism=delivery_mechanism)

    instruction = PaymentInstructionFactory(fsp=fsp, payload={"config_key": "test_config"})

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
    instruction = PaymentInstructionFactory(fsp=fsp, payload={"config_key": "non_existent_config"})

    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})

    with pytest.raises(FinancialServiceProviderConfigFactory._meta.model.DoesNotExist):
        payment_record_admin_instance.configuration(payment_record_admin_instance, request, payment_record.pk)
