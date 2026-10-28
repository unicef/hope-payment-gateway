from hope_payment_gateway.api.western_union.filters import (
    CorridorFilter,
    ServiceProviderCodeFilter,
)
from hope_payment_gateway.api.western_union.serializers import (
    CorridorSerializer,
    ServiceProviderCodeSerializer,
)
from hope_payment_gateway.apps.core.grant import Grant
from hope_payment_gateway.apps.core.permissions import GrantPermission
from hope_payment_gateway.apps.fsp.western_union.models import (
    Corridor,
    ServiceProviderCode,
)
from hope_api_auth.views import TokenRequiredView
from rest_framework import permissions as drf_permissions
from rest_framework.viewsets import ModelViewSet


class GrantRequiredTokenView(TokenRequiredView):
    permission_classes = [GrantPermission]
    permission = Grant.API_READ_ONLY

    def get_permissions(self):
        if self.request.method in drf_permissions.SAFE_METHODS:
            self.permission = Grant.API_READ_ONLY
        else:
            action = getattr(self, "action", None)
            if action == "destroy":
                self.permission = Grant.API_PLAN_MANAGE
            else:
                self.permission = Grant.API_PLAN_MANAGE
        return super().get_permissions()


class ProtectedMixin:
    def destroy(self, request, pk=None):
        raise NotImplementedError


class CorridorViewSet(ProtectedMixin, ModelViewSet, GrantRequiredTokenView):
    serializer_class = CorridorSerializer
    queryset = Corridor.objects.all()

    filterset_class = CorridorFilter
    search_fields = ["description"]


class ServiceProviderCodeViewSet(ProtectedMixin, ModelViewSet, GrantRequiredTokenView):
    serializer_class = ServiceProviderCodeSerializer
    queryset = ServiceProviderCode.objects.all()

    filterset_class = ServiceProviderCodeFilter
    search_fields = ["description", "code"]
