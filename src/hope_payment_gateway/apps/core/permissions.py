import typing
from typing import Any

from constance import config
from rest_framework import permissions
from rest_framework.request import Request

from hope_payment_gateway.apps.core.grant import Grant


if typing.TYPE_CHECKING:
    from rest_framework.request import Request


def get_client_ip(request):
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].split(":")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class WhitelistPermission(permissions.BasePermission):
    """Global permission check for whitelisted IPs."""

    def has_permission(self, request, view):
        if config.WHITELIST_ENABLED:
            return get_client_ip(request) in config.WHITELISTED_IPS.split(";")
        return True


class HasAnyPermission(permissions.BasePermission):
    """Permission that checks if a user has *at least one* of the given Django permissions."""

    required_permissions = []

    def has_permission(self, request, view):
        perms = getattr(view, "required_permissions", self.required_permissions)
        if not perms:
            return False

        return any(request.user.has_perm(p) for p in perms)


class GrantPermission(permissions.BasePermission):
    """Authorize a token using the grant required by the current view.

    ``GrantRequiredTokenView`` exposes the required grant through its
    ``permission`` property. Grants are ordered, so a token is allowed when any
    of its grants is at least as privileged as the required one.
    """

    def has_permission(self, request: "Request", view: Any) -> bool:
        auth = getattr(request, "auth", None)
        if not auth:
            return False

        user = request.user
        if user and getattr(user, "is_superuser", False):
            return True

        required = getattr(view, "permission", None)
        if not isinstance(required, Grant):
            return False

        grants = getattr(auth, "grants", None) or []
        return any(self._level(grant) >= required.level for grant in grants)

    @staticmethod
    def _level(grant: Any) -> int:
        member = Grant.__members__.get(grant)
        return member.level if member else -1
