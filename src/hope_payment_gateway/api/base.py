from typing import TYPE_CHECKING, Any, ClassVar

from hope_api_auth.views import TokenRequiredView
from rest_framework import permissions as drf_permissions

from hope_payment_gateway.apps.core.grant import Grant
from hope_payment_gateway.apps.core.permissions import GrantPermission

if TYPE_CHECKING:  # pragma: no cover
    from rest_framework.request import Request
    from rest_framework.response import Response


class GrantRequiredTokenView(TokenRequiredView):  # type: ignore[misc]
    """Token-authenticated view that selects the required grant per request.

    Subclasses can configure the grants required for reads, writes and specific
    actions. Actions that change the state of a payment plan always require
    ``API_PLAN_MANAGE`` unless explicitly overridden in ``action_grants``.
    """

    permission_classes = [GrantPermission]

    read_grant: Grant = Grant.API_READ_ONLY
    write_grant: Grant = Grant.API_PLAN_UPLOAD
    manage_actions: ClassVar[frozenset[str]] = frozenset(
        {"cancel", "open", "ready", "close", "finalize", "process", "abort", "destroy"}
    )
    action_grants: ClassVar[dict[str, Grant]] = {}

    @property
    def permission(self) -> Grant:
        if self.request.method in drf_permissions.SAFE_METHODS:
            return self.read_grant
        action = getattr(self, "action", "")
        if action in self.action_grants:
            return self.action_grants[action]
        if action in self.manage_actions:
            return Grant.API_PLAN_MANAGE
        return self.write_grant


class ProtectedMixin:
    def destroy(self, request: "Request", *args: Any, **kwargs: Any) -> "Response":
        raise NotImplementedError
