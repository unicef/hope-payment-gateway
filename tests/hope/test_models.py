import pytest

from hope_payment_gateway.apps.hope.models import (
    BusinessArea,
    PaymentRecord,
    ReadOnlyModelException,
)
from tests.factories import BusinessAreaFactory


def test_readonly_create_fail_models(django_app, admin_user):
    with pytest.raises(ReadOnlyModelException):
        BusinessAreaFactory()


def test_readonly_change_fail_models(django_app, admin_user):
    with pytest.raises(ReadOnlyModelException):
        ba = BusinessArea.objects.first()
        ba.save()


def test_readonly_delete_fail_models(django_app, admin_user):
    with pytest.raises(ReadOnlyModelException):
        ba = BusinessArea.objects.first()
        ba.delete()


def test_limited_create_fail_models(django_app, admin_user):
    with pytest.raises(ReadOnlyModelException):
        BusinessAreaFactory()


def test_limited_change_ok_fail_models(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    assert payment.conflicted is False
    payment.conflicted = True
    payment.save()
    assert payment.conflicted is True


def test_limited_change_ko_fail_models(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    assert payment.excluded is False
    payment.excluded = True
    payment.save()
    payment.refresh_from_db()
    assert payment.excluded is False


def test_limited_delete_fail_models(django_app, admin_user):
    with pytest.raises(ReadOnlyModelException):
        payment = PaymentRecord.objects.first()
        payment.delete()
