from typing import Any

from django.http import HttpRequest
from django.http.response import HttpResponseBase
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .auth import GrantedPermission, LoggingTokenAuthentication
from .models import APILogEntry, Grant


class LoggingAPIView(APIView):
    permission_classes = [
        GrantedPermission,
    ]
    authentication_classes = [LoggingTokenAuthentication]
    permission = Grant.API_READ_ONLY
    log_http_methods = ["POST", "PUT", "DELETE"]

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        ret = super().dispatch(request, *args, **kwargs)
        if (
            request.method.upper() in self.log_http_methods
            and (ret.status_code < 300 or ret.status_code > 400)
            and request.auth
        ):
            APILogEntry.objects.create(
                token=request.auth,
                url=request.path,
                method=request.method.upper(),
                status_code=ret.status_code,
            )

        return ret

    def handle_exception(self, exc: Exception) -> Any:
        if isinstance(exc, PermissionDenied):
            perm_name = self.permission.name if self.permission else ""
            exc = PermissionDenied("%s %s" % (exc.detail, perm_name))

        return super().handle_exception(exc)


class LoggingAPIViewSet(ModelViewSet, LoggingAPIView):
    pass
