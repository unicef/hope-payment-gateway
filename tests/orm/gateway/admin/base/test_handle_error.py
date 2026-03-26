from unittest.mock import Mock

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite

from hope_payment_gateway.apps.gateway.admin.base import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord


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
