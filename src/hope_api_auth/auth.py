from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from .models import APIToken

User = get_user_model()


class LoggingTokenAuthentication(TokenAuthentication):
    keyword = "Token"
    model = APIToken

    def authenticate_credentials(self, key: str) -> tuple[User, APIToken]:
        try:
            token = (
                APIToken.objects.select_related("user")
                .filter(valid_from__lte=timezone.now())
                .filter(Q(valid_to__gte=timezone.now()) | Q(valid_to__isnull=True))
                .get(key=key)
            )
        except APIToken.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return token.user, token


class GrantedPermission(IsAuthenticated):
    def has_permission(self, request: Request, view: Any) -> bool:
        if bool(request.auth):
            if view.permission == "any" or request.user and request.user.is_authenticated and request.user.is_superuser:
                return True
            if view.permission:
                return view.permission.name in request.auth.grants

        return False
