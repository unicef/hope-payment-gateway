from unittest.mock import patch

from django.urls import reverse

import pytest

from hope_payment_gateway.apps.hope.models import PaymentRecord


@pytest.mark.parametrize(
    "model", ["businessarea", "programme", "financialserviceprovider", "paymentplan", "paymentrecord"]
)
def test_admin_models_list(django_app, admin_user, model):
    url = reverse(f"admin:hope_{model}_changelist")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "model",
    ["businessarea", "programme", "programme_cycle", "financialserviceprovider", "paymentplan", "paymentrecord"],
)
def test_admin_models_detail(django_app, admin_user, model):
    payment = PaymentRecord.objects.first()
    url = reverse(f"admin:hope_{model}_change", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code in [200, 302]


def test_admin_send_money_validation(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_validation", args=[payment.pk])
    with patch("hope_payment_gateway.apps.western_union.endpoints.send_money_validation.send_money_validation"):
        django_app.get(url, user=admin_user)


def test_admin_send_money_store(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_store", args=[payment.pk])
    with patch("hope_payment_gateway.apps.western_union.endpoints.send_money_store.send_money_store"):
        django_app.get(url, user=admin_user)


def test_admin_search_request(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_search_request", args=[payment.pk])
    with patch("hope_payment_gateway.apps.western_union.endpoints.search_request.search_request"):
        django_app.get(url, user=admin_user)


def test_admin_cancel_request(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_cancel_request", args=[payment.pk])
    with patch("hope_payment_gateway.apps.western_union.endpoints.cancel_request.cancel_request"):
        django_app.get(url, user=admin_user)


def test_admin_cancel_complete(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_cancel_complete", args=[payment.pk])
    with patch("hope_payment_gateway.apps.western_union.endpoints.cancel_complete.cancel_complete"):
        django_app.get(url, user=admin_user)
