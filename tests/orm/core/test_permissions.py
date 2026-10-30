from types import SimpleNamespace
from unittest.mock import patch

import pytest
from constance.test import override_config
from django.test import RequestFactory, override_settings
from django.urls import reverse

from hope_payment_gateway.apps.core.grant import Grant
from hope_payment_gateway.apps.core.permissions import (
    GrantPermission,
    WhitelistPermission,
    get_client_ip,
)
from tests.perms import user_grant_permissions


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def permission_user(user):
    return user


def test_get_client_ip_with_x_forwarded_for(request_factory):
    request = request_factory.get("/admin", HTTP_X_FORWARDED_FOR="192.168.1.1, 10.0.0.1")
    assert get_client_ip(request) == "192.168.1.1"


def test_get_client_ip_without_x_forwarded_for(request_factory):
    request = request_factory.get("/admin")
    assert get_client_ip(request) == request.META.get("REMOTE_ADDR")


@pytest.mark.parametrize(("ip", "expected"), [("127.0.0.1", True), ("192.168.1.1", False)])
@pytest.mark.django_db
@override_settings(DEBUG=False, WHITELISTED_IPS="127.0.0.1")
def test_whitelist_permission_allowed(request_factory, ip, expected):
    request = request_factory.get("/admin", HTTP_X_FORWARDED_FOR=ip)
    permission = WhitelistPermission()
    assert permission.has_permission(request, None) is expected


@pytest.mark.django_db
def test_whitelist_permission_denied(request_factory):
    request = request_factory.get("/admin", HTTP_X_FORWARDED_FOR="10.0.0.2")
    permission = WhitelistPermission()
    assert not permission.has_permission(request, None)


@pytest.mark.django_db
def test_whitelist_permission_bypass_debug(request_factory):
    with override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True):
        request = request_factory.get("/admin")
        permission = WhitelistPermission()
        assert permission.has_permission(request, None)


@pytest.mark.django_db
@override_config(WHITELIST_ENABLED=False)
def test_whitelist_disabled_permission(request_factory):
    request = request_factory.get("/admin")
    permission = WhitelistPermission()
    assert permission.has_permission(request, None)


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.views.ftp.FTPClient")
def test_has_any_permission_view(mock_patch, permission_user, api_client):
    api_client.force_authenticate(user=permission_user)
    url = reverse("rest:wu-files-list")

    response = api_client.get(url)
    assert response.status_code == 403

    with user_grant_permissions(permission_user, "core.can_access_ftp"):
        response = api_client.get(url)
        assert response.status_code in [200, 400]


def _grant_request(request_factory, grants):
    request = request_factory.get("/")
    request.auth = SimpleNamespace(grants=grants)
    request.user = SimpleNamespace(is_superuser=False)
    return request


class _ManageView:
    permission = Grant.API_PLAN_MANAGE


def test_grant_permission_denies_request_without_auth(request_factory):
    request = request_factory.get("/")
    request.auth = None
    request.user = SimpleNamespace(is_superuser=False)

    assert GrantPermission().has_permission(request, _ManageView()) is False


def test_grant_permission_denies_view_without_grant(request_factory):
    request = _grant_request(request_factory, [Grant.API_PLAN_MANAGE.name])

    assert GrantPermission().has_permission(request, SimpleNamespace()) is False


def test_grant_permission_allows_sufficient_grant(request_factory):
    request = _grant_request(request_factory, [Grant.API_PLAN_MANAGE.name])

    assert GrantPermission().has_permission(request, _ManageView()) is True


def test_grant_permission_denies_insufficient_grant(request_factory):
    request = _grant_request(request_factory, [Grant.API_READ_ONLY.name])

    assert GrantPermission().has_permission(request, _ManageView()) is False


def test_grant_permission_ignores_unknown_grants(request_factory):
    request = _grant_request(request_factory, ["NOT_A_GRANT", Grant.API_PLAN_MANAGE.name])

    assert GrantPermission().has_permission(request, _ManageView()) is True


def test_grant_permission_level_for_unknown_grant():
    assert GrantPermission._level("NOT_A_GRANT") == -1
    assert GrantPermission._level(Grant.API_PLAN_MANAGE.name) == Grant.API_PLAN_MANAGE.level
