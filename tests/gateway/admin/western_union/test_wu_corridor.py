import pytest
from django.urls import reverse
from constance.test import override_config

from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import (
    PaymentInstructionFactory,
    PaymentRecordFactory,
    CorridorFactory,
)


@pytest.fixture
def western_union_admin_instance(admin_site) -> PaymentRecordAdmin:
    return PaymentRecordAdmin(PaymentRecord, admin_site)


@pytest.fixture
def payment_record(wu):
    instruction = PaymentInstructionFactory(fsp=wu)
    return PaymentRecordFactory(parent=instruction)


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_wu_corridor_success(user, western_union_admin_instance, payment_record, client):
    payment_record.payload = {
        "delivery_services_code": "800",
        "destination_country": "US",
        "destination_currency": "USD",
    }
    payment_record.save()

    corridor = CorridorFactory(
        destination_country="US",
        destination_currency="USD",
    )

    client.force_login(user)
    url = reverse("admin:gateway_paymentrecord_wu_corridor", args=[payment_record.pk])
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("admin:western_union_corridor_change", args=[corridor.pk])
