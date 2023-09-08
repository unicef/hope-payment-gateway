from unittest.mock import patch

from django.urls import reverse

import pytest

from hope_payment_gateway.apps.hope.models import PaymentRecord


@pytest.mark.parametrize(
    "model", ["businessarea", "programme", "programmecycle", "financialserviceprovider", "paymentplan", "paymentrecord"]
)
def test_admin_models_list(django_app, admin_user, model):
    url = reverse(f"admin:hope_{model}_changelist")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "model",
    ["businessarea", "programme", "programmecycle", "financialserviceprovider", "paymentplan", "paymentrecord"],
)
def test_admin_models_detail(django_app, admin_user, model):
    payment = PaymentRecord.objects.first()
    url = reverse(f"admin:hope_{model}_change", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code in [200, 302]


@patch("hope_payment_gateway.apps.hope.admin.send_money_validation")
def test_admin_send_money_validation(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_validation", args=[payment.pk])
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.hope.admin.send_money")
def test_admin_send_money(django_app, admin_user):
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money", args=[payment.pk])
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.hope.admin.search_request")
def test_admin_search_request(django_app, admin_user):
    payment = PaymentRecord.objects.filter(unicef_id__isnull=False).first()
    url = reverse("admin:hope_paymentrecord_search_request", args=[payment.pk])
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.hope.admin.cancel")
def test_admin_cancel_complete(django_app, admin_user):
    payment = PaymentRecord.objects.filter(unicef_id__isnull=False).first()
    url = reverse("admin:hope_paymentrecord_cancel", args=[payment.pk])
    django_app.get(url, user=admin_user)
