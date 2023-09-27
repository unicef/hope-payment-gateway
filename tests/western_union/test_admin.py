from unittest.mock import patch

from django.urls import reverse


def test_admin_request(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.requests_request"):
        url = reverse("admin:western_union_corridor_request")
        django_app.get(url, user=admin_user)


def test_admin_das_countries_currencies(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_countries_currencies"):
        url = reverse("admin:western_union_corridor_das_countries_currencies")
        django_app.get(url, user=admin_user)


def test_admin_das_destination_countries(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_destination_countries"):
        url = reverse("admin:western_union_corridor_das_destination_countries")
        django_app.get(url, user=admin_user)


def test_admin_das_origination_currencies(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_origination_currencies"):
        url = reverse("admin:western_union_corridor_das_origination_currencies")
        django_app.get(url, user=admin_user)


def test_admin_das_destination_currencies(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_destination_currencies"):
        url = reverse("admin:western_union_corridor_das_destination_currencies")
        django_app.get(url, user=admin_user)


def test_admin_das_delivery_services(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_delivery_services"):
        url = reverse("admin:western_union_corridor_das_delivery_services")
        django_app.get(url, user=admin_user)


def test_admin_das_delivery_option_template(django_app, admin_user):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_delivery_option_template"):
        url = reverse("admin:western_union_corridor_das_delivery_option_template")
        django_app.get(url, user=admin_user)


def test_admin_das_delivery_services_detail(django_app, admin_user, corridor):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_delivery_services"):
        url = reverse("admin:western_union_corridor_delivery_services", args=[corridor.pk])
        django_app.get(url, user=admin_user)


def test_admin_das_delivery_option_template_detail(django_app, admin_user, corridor):
    with patch("hope_payment_gateway.apps.fsp.western_union.admin.das_delivery_option_template"):
        url = reverse("admin:western_union_corridor_delivery_option_template", args=[corridor.pk])
        django_app.get(url, user=admin_user)


#
# def test_admin_send_money_validation(django_app, admin_user, prl):
#     with patch("hope_payment_gateway.apps.fsp.western_union.admin.send_money_validation"):
#         url = reverse("admin:western_union_paymentrecordlog_send_money_validation", args=[prl.pk])
#         django_app.get(url, user=admin_user)
#
#
# def test_admin_send_money(django_app, admin_user, prl):
#     with patch("hope_payment_gateway.apps.fsp.western_union.admin.send_money"):
#         url = reverse("admin:western_union_paymentrecordlog_send_money", args=[prl.pk])
#         django_app.get(url, user=admin_user)
#
#
# def test_admin_search_request(django_app, admin_user, prl):
#     with patch("hope_payment_gateway.apps.fsp.western_union.admin.search_request"):
#         url = reverse("admin:western_union_paymentrecordlog_search_request", args=[prl.pk])
#         django_app.get(url, user=admin_user)
#
#
# def test_admin_cancel(django_app, admin_user, prl):
#     with patch("hope_payment_gateway.apps.fsp.western_union.admin.cancel"):
#         url = reverse("admin:western_union_paymentrecordlog_cancel", args=[prl.pk])
#         django_app.get(url, user=admin_user)
