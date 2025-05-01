import pytest
from django.test import RequestFactory, override_settings
from constance.test import override_config
from hope_payment_gateway.apps.core.permissions import WhitelistPermission, get_client_ip


@pytest.fixture
def request_factory():
    return RequestFactory()


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
