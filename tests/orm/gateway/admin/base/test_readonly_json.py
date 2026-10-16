import pytest
from django.contrib import admin
from django.urls import reverse

from hope_payment_gateway.apps.core.admin_site import PrettyJSONAdminMixin
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from tests.factories.payment import PaymentInstructionFactory, PaymentRecordFactory
from tests.factories.user import SuperUserFactory


def test_registered_admin_gets_pretty_json_mixin():
    assert isinstance(admin.site._registry[PaymentRecord], PrettyJSONAdminMixin)


def test_json_field_names_are_detected():
    model_admin = admin.site._registry[PaymentRecord]

    assert {"fsp_data", "extra_data", "payload"} <= model_admin._json_field_names()


def test_all_json_fields_have_readonly_display():
    model_admin = admin.site._registry[PaymentRecord]

    readonly = model_admin.get_readonly_fields(None, PaymentRecord())
    assert {"payload_display", "fsp_data_display", "extra_data_display"} <= set(readonly)
    assert {"fsp_data", "extra_data", "payload"}.isdisjoint(readonly)


def test_all_json_fields_are_excluded_from_the_form():
    model_admin = admin.site._registry[PaymentRecord]

    excluded = model_admin.get_exclude(None, PaymentRecord())
    assert {"fsp_data", "extra_data", "payload"} <= set(excluded)


@pytest.fixture
def app(django_app_factory):
    admin_user = SuperUserFactory.create(username="superuser")
    django_app = django_app_factory(csrf_checks=False)
    django_app.set_user(admin_user)
    django_app._user = admin_user
    return django_app


@pytest.mark.django_db
def test_all_json_fields_render_as_pretty_json(app):
    instruction = PaymentInstructionFactory.create(payload={"a": 1})
    record = PaymentRecordFactory.create(parent=instruction, fsp_data={"foo": "bar"}, payload={"x": 2})
    url = reverse("admin:gateway_paymentrecord_change", args=[record.pk])

    res = app.get(url)
    content = res.content.decode()

    assert res.status_code == 200
    for field in ("fsp_data", "extra_data", "payload"):
        assert f'id="id_{field}"' not in content
    assert "<pre>" in content
    assert '"foo": "bar"' in content
    assert '"x": 2' in content
