import pytest
from constance.test import override_config
from django.test import RequestFactory

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
)


@pytest.fixture
def payment_record_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def req(user):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    return request


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_palpay_button_visible(req, payment_record_admin_instance, palpay):
    instruction = PaymentInstructionFactory.create(fsp=palpay)
    payment_record = PaymentRecordFactory.create(parent=instruction)
    req.original = payment_record
    payment_record_admin_instance.palpay.func(payment_record_admin_instance, req)
    assert len(req.choices) == 7


@pytest.mark.django_db
@override_config(PALPAY_VENDOR_NUMBER="XYZ")
def test_palpay_button_hidden_for_other_fsp(req, payment_record_admin_instance, mg):
    instruction = PaymentInstructionFactory.create(fsp=mg)
    payment_record = PaymentRecordFactory.create(parent=instruction)
    req.original = payment_record
    payment_record_admin_instance.palpay.func(payment_record_admin_instance, req)
    assert req.visible is False
