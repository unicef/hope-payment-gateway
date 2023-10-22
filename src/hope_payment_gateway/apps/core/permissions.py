from django.conf import settings

from constance import config
from rest_framework import permissions


class WhitelistPermission(permissions.BasePermission):
    """
    Global permission check for whitelisted IPs.
    """

    def has_permission(self, request, view):
        domain = request.META.get("REMOTE_HOST", None)
        return domain in config.WESTERN_UNION_WHITELISTED_IPS.split(";") or settings.DEBUG
