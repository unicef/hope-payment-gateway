import pytest
from constance.test import override_config
from django.test import RequestFactory

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from perms import user_grant_permissions
from tests.factories.payment import (
    DeliveryMechanismFactory,
    FinancialServiceProviderConfigFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    CorridorFactory,
)


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def payment_record(wu):
    instruction = PaymentInstructionFactory(fsp=wu)
    return PaymentRecordFactory(parent=instruction)


@pytest.fixture
def req(user):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    return request


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_western_union_button_visibility_for_wu_fsp(req, payment_record, payment_record_admin_instance):
    req.original = payment_record
    with user_grant_permissions(req.user, "western_union.can_check_status"):
        payment_record_admin_instance.western_union(payment_record_admin_instance, req)
        assert len(req.choices) >= 7


@pytest.mark.django_db
def test_western_union_button_visibility_for_non_wu_fsp(req, payment_record, payment_record_admin_instance):
    with user_grant_permissions(req.user, "western_union.can_check_status"):
        req.original = payment_record
        payment_record_admin_instance.western_union(payment_record_admin_instance, req)
        assert req.visible is False


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_western_union_button_with_corridor(req, payment_record, payment_record_admin_instance):
    req.original = payment_record

    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
    }

    CorridorFactory(destination_country="US", destination_currency="USD")

    with user_grant_permissions(req.user, "western_union.can_check_status"):
        payment_record_admin_instance.western_union(payment_record_admin_instance, req)
        assert any(choice.name == "wu_corridor" for choice in req.choices)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_western_union_button_with_configuration(wu, req, payment_record_admin_instance):
    delivery_mechanism = DeliveryMechanismFactory(code="CASH")

    FinancialServiceProviderConfigFactory(key="test_config", fsp=wu, delivery_mechanism=delivery_mechanism)
    instruction = PaymentInstructionFactory(fsp=wu, payload={"config_key": "test_config"})
    payment_record = PaymentRecordFactory(parent=instruction, payload={"delivery_mechanism": "CASH"})
    req.original = payment_record

    with user_grant_permissions(req.user, "western_union.can_check_status"):
        payment_record_admin_instance.western_union(payment_record_admin_instance, req)
        assert any(choice.name == "configuration" for choice in req.choices)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_western_union_button_without_corridor(req, payment_record, payment_record_admin_instance):
    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
    }
    CorridorFactory(destination_country="", destination_currency="")
    req.original = payment_record

    with user_grant_permissions(req.user, "western_union.can_check_status"):
        payment_record_admin_instance.western_union(payment_record_admin_instance, req)
        assert not any(choice.name == "wu_corridor" for choice in req.choices)
