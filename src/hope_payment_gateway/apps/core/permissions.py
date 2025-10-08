from constance import config
from rest_framework import permissions


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
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
