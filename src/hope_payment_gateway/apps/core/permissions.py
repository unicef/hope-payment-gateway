from django.conf import settings

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
    """
    Global permission check for whitelisted IPs.
    """

    def has_permission(self, request, view):
        if config.WHITELIST_ENABLED:
            return get_client_ip(request) in config.WHITELISTED_IPS.split(";")
        return True
