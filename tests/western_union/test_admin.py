from unittest.mock import patch

from django.urls import reverse


@patch("hope_payment_gateway.apps.western_union.endpoints.request.requests_request")
def test_admin_request(django_app, admin_user):
    url = reverse("admin:western_union_corridor_request")
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.western_union.endpoints.das.das_countries_currencies")
def test_admin_das_countries_currencies(django_app, admin_user):
    url = reverse("admin:western_union_corridor_das_countries_currencies")
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.western_union.endpoints.das.das_origination_currencies")
def test_admin_das_origination_currencies(django_app, admin_user):
    url = reverse("admin:western_union_corridor_das_origination_currencies")
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.western_union.endpoints.das.das_destination_currencies")
def test_admin_das_destination_currencies(django_app, admin_user):
    url = reverse("admin:western_union_corridor_das_destination_currencies")
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.western_union.endpoints.das.das_delivery_services")
def test_admin_das_delivery_services(django_app, admin_user):
    url = reverse("admin:western_union_corridor_das_delivery_services")
    django_app.get(url, user=admin_user)


@patch("hope_payment_gateway.apps.western_union.endpoints.das.das_delivery_option_template")
def test_admin_das_delivery_option_template(django_app, admin_user):
    url = reverse("admin:western_union_corridor_das_delivery_option_template")
    django_app.get(url, user=admin_user)
