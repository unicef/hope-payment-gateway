import pytest
from constance.test import override_config
from django.test import RequestFactory

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


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
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_moneygram_button_visibility_for_mg_fsp(req, payment_record, payment_record_admin_instance):
    req.original = payment_record
    payment_record_admin_instance.moneygram(payment_record_admin_instance, req)
    assert len(req.choices) >= 7


@pytest.mark.django_db
def test_moneygram_button_visibility_for_non_mg_fsp(req, payment_record, payment_record_admin_instance):
    req.original = payment_record
    payment_record_admin_instance.moneygram(payment_record_admin_instance, req)
    assert req.visible is False


@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_moneygram_button_with_configuration(mg, req, payment_record_admin_instance):
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")

    FinancialServiceProviderConfigFactory(key="test_config", fsp=mg, delivery_mechanism=delivery_mechanism)
    instruction = PaymentInstructionFactory(fsp=mg, payload={"config_key": "test_config"})
    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})
    req.original = payment_record

    payment_record_admin_instance.moneygram(payment_record_admin_instance, req)
    assert any(choice.name == "configuration" for choice in req.choices)


@pytest.mark.django_db
@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
def test_moneygram_button_without_configuration(req, payment_record, payment_record_admin_instance):
    payment_record.payload = {"delivery_mechanism": "CASH"}
    req.original = payment_record

    payment_record_admin_instance.moneygram(payment_record_admin_instance, req)
    assert not any(choice.name == "configuration" for choice in req.choices)
