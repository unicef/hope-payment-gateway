from typing import Any

from django.http import HttpRequest
from django.http.response import HttpResponseBase

from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from django.conf import settings
from .auth import GrantedPermission, LoggingTokenAuthentication
from .models import APILogEntry, Grant


class LoggingAPIView(APIView):
    permission_classes = [GrantedPermission]
    authentication_classes = [LoggingTokenAuthentication]
    permission = Grant.API_READ_ONLY
    log_http_methods = ["POST", "PUT", "DELETE"]

    # temporary for local development
    def get_authenticators(self):  # TODO remove me
        auth_classes = super().get_authenticators()
        if settings.DEBUG:
            from rest_framework.authentication import BasicAuthentication
            auth_classes.append(BasicAuthentication())
            return auth_classes
        return auth_classes

    def get_permissions(self):  # TODO remove me
        if settings.DEBUG:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        ret = super().dispatch(request, *args, **kwargs)
        if request.method.upper() in self.log_http_methods and (ret.status_code < 300 or ret.status_code > 400):
            if request.auth:
                log = APILogEntry.objects.create(
                    token=request.auth,
                    url=request.path,
                    method=request.method.upper(),
                    status_code=ret.status_code,
                )
                assert log.pk

        return ret

    def handle_exception(self, exc: Exception) -> Any:
        if isinstance(exc, PermissionDenied):
            perm_name = self.permission.name if self.permission else ""
            exc = PermissionDenied("%s %s" % (exc.detail, perm_name))

        return super().handle_exception(exc)


class LoggingAPIViewSet(ModelViewSet, LoggingAPIView):
    pass
