from unittest.mock import Mock

import pytest
from django.urls import reverse
from django.test import RequestFactory
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from hope_payment_gateway.apps.gateway.admin.base import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories import UserFactory
from tests.factories.payment import (
    FinancialServiceProviderFactory,
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def admin_instance():
    admin_site = AdminSite()
    return PaymentRecordAdmin(PaymentRecord, admin_site)


def test_handle_error_500(admin_instance):
    resp = Mock()
    resp.status_code = 500
    resp.data = {"error": "Something went wrong"}
    expected_message = ["Something went wrong"]
    expected_loglevel = messages.ERROR
    loglevel, msgs = admin_instance.handle_error(resp)
    assert loglevel == expected_loglevel
    assert msgs == expected_message


def test_handle_error_400(admin_instance):
    resp = Mock()
    resp.status_code = 400
    resp.data = {"error": "Something went wrong"}
    expected_message = ["Something went wrong"]
    expected_loglevel = messages.WARNING
    loglevel, msgs = admin_instance.handle_error(resp)
    assert loglevel == expected_loglevel
    assert msgs == expected_message


@pytest.mark.django_db
def test_configuration_view_redirects_correctly(admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = UserFactory()

    fsp = FinancialServiceProviderFactory()
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")
    config = FinancialServiceProviderConfigFactory(key="test_config", fsp=fsp, delivery_mechanism=delivery_mechanism)

    instruction = PaymentInstructionFactory(fsp=fsp, extra={"config_key": "test_config"})

    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})

    response = admin_instance.configuration(admin_instance, request, payment_record.pk)

    expected_url = reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk])
    assert response.url == expected_url


@pytest.mark.django_db
def test_configuration_view_handles_missing_config(admin_instance):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = UserFactory()

    fsp = FinancialServiceProviderFactory()
    instruction = PaymentInstructionFactory(fsp=fsp, extra={"config_key": "non_existent_config"})

    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})

    with pytest.raises(FinancialServiceProviderConfigFactory._meta.model.DoesNotExist):
        admin_instance.configuration(admin_instance, request, payment_record.pk)
