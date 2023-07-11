from django.urls import reverse

import pytest


@pytest.mark.parametrize(
    "model", ["businessarea", "programme", "financialserviceprovider", "paymentplan", "paymentrecord"]
)
def test_admin_models(django_app, admin_user, model):
    url = reverse(f"admin:hope_{model}_changelist")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200
