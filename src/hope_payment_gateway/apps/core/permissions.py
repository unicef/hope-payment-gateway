from typing import Any, ClassVar, TYPE_CHECKING

from constance import config
from hope_api_auth.views import TokenRequiredView
from rest_framework import permissions

from hope_payment_gateway.apps.core.grant import Grant

if TYPE_CHECKING:
    from rest_framework.request import Request


def _grant_level(grant: Any) -> int:
    if isinstance(grant, Grant):
        return grant.level
    try:
        return Grant(grant).level
    except TypeError, ValueError:
        return -1


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


class GrantTierPermission(permissions.IsAuthenticated):
    """Authorize API tokens using a hierarchy of grants.

    A token is authorized when it holds a grant at least as privileged as the
    one required by the current request. This keeps ``API_READ_ONLY`` tokens
    read-only while allowing the higher tiers to read as well as write.
    """

    def has_permission(self, request: "Request", view: Any) -> bool:
        if not request.auth:
            return False

        required = getattr(view, "permission", None)
        if required == "any":
            return True

        user = request.user
        if user and user.is_authenticated and user.is_superuser:
            return True

        if not isinstance(required, Grant):
            return False

        grants = getattr(request.auth, "grants", None) or []
        return any(_grant_level(grant) >= required.level for grant in grants)


class GrantRequiredView(TokenRequiredView):  # type: ignore[misc]
    """``TokenRequiredView`` that selects the required grant per HTTP method/action."""

    permission_classes: list[type[permissions.BasePermission]] = [GrantTierPermission]
    read_grant: Grant = Grant.API_READ_ONLY
    write_grant: Grant = Grant.API_PLAN_MANAGE
    action_grants: ClassVar[dict[str, Grant]] = {}

    @property
    def permission(self) -> Grant:
        if self.request.method in permissions.SAFE_METHODS:
            return self.read_grant
        return self.action_grants.get(getattr(self, "action", ""), self.write_grant)


class GrantPermission(permissions.BasePermission):
    """Method-aware grant permission.

    - SAFE_METHODS (GET, HEAD, OPTIONS): require API_READ_ONLY or higher
    - POST/PUT/PATCH/DELETE: require appropriate write grant.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        if not getattr(request, "auth", None):
            return False
        if request.user and getattr(request.user, "is_superuser", False):
            return True

        grants = self._get_grants(request)
        if not grants:
            return False

        if request.method in permissions.SAFE_METHODS:
            return self._has_read_access(grants)

        action = getattr(view, "action", None)
        return self._has_write_access(grants, view, action)

    def _get_grants(self, request: Request) -> set[str]:
        grants: set[str] = set()
        auth = request.auth
        if not hasattr(auth, "grants") or not auth.grants:
            return grants
        for g in auth.grants:
            if isinstance(g, str):
                grants.add(g)
                continue
            if hasattr(g, "name"):
                grants.add(g.name)
                continue
            if hasattr(g, "value"):
                try:
                    grants.add(Grant(g).name)
                except TypeError, ValueError:
                    grants.add(str(g))
        return grants

    @staticmethod
    def _has_read_access(grants: set[str]) -> bool:
        if Grant.API_READ_ONLY.name in grants:
            return True
        return Grant.API_PLAN_UPLOAD.name in grants or Grant.API_PLAN_MANAGE.name in grants

    def _has_write_access(self, grants: set[str], view: Any, action: str | None) -> bool:
        if hasattr(view, "required_grant_for_action") and action:
            required = view.required_grant_for_action.get(action)
            if required:
                required_name = required.name if isinstance(required, Grant) else str(required)
                return required_name in grants or self._has_higher_grant(grants, required)

        if hasattr(view, "write_permission"):
            required = view.write_permission
            required_name = required.name if isinstance(required, Grant) else str(required)
            return required_name in grants or self._has_higher_grant(grants, required)

        if action in ["cancel", "open", "ready", "close", "finalize", "process", "abort", "destroy", "delete"]:
            return Grant.API_PLAN_MANAGE.name in grants

        if action in ["create", "update", "partial_update", "add_records"]:
            return Grant.API_PLAN_UPLOAD.name in grants or Grant.API_PLAN_MANAGE.name in grants

        return Grant.API_PLAN_MANAGE.name in grants

    def _has_higher_grant(self, grants: set, required: Grant) -> bool:
        required_level = list(Grant).index(required)
        for grant_name in grants:
            try:
                grant = Grant[grant_name]
                if list(Grant).index(grant) >= required_level:
                    return True
            except KeyError, ValueError:
                continue
        return False


class ReadOnlyGrantPermission(GrantPermission):
    """For read-only operations only."""


class PlanUploadGrantPermission(GrantPermission):
    """For plan upload operations."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if not getattr(request, "auth", None):
            return False
        if request.user and getattr(request.user, "is_superuser", False):
            return True

        grants = set()
        auth = request.auth
        if hasattr(auth, "grants") and auth.grants:
            for g in auth.grants:
                if isinstance(g, str):
                    grants.add(g)
                elif hasattr(g, "name"):
                    grants.add(g.name)

        if not grants:
            return False

        if request.method in permissions.SAFE_METHODS:
            return (
                Grant.API_READ_ONLY.name in grants
                or Grant.API_PLAN_UPLOAD.name in grants
                or Grant.API_PLAN_MANAGE.name in grants
            )

        # Write operations need plan upload or manage
        return Grant.API_PLAN_UPLOAD.name in grants or Grant.API_PLAN_MANAGE.name in grants


class PlanManageGrantPermission(GrantPermission):
    """For plan management operations including state changes."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if not getattr(request, "auth", None):
            return False
        if request.user and getattr(request.user, "is_superuser", False):
            return True

        grants = set()
        auth = request.auth
        if hasattr(auth, "grants") and auth.grants:
            for g in auth.grants:
                if isinstance(g, str):
                    grants.add(g)
                elif hasattr(g, "name"):
                    grants.add(g.name)

        if not grants:
            return False

        if request.method in permissions.SAFE_METHODS:
            return (
                Grant.API_READ_ONLY.name in grants
                or Grant.API_PLAN_UPLOAD.name in grants
                or Grant.API_PLAN_MANAGE.name in grants
            )

        return Grant.API_PLAN_MANAGE.name in grants
