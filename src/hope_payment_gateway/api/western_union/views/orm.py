from rest_framework.viewsets import ModelViewSet

from hope_payment_gateway.api.base import GrantRequiredTokenView, ProtectedMixin
from hope_payment_gateway.api.western_union.filters import (
    CorridorFilter,
    ServiceProviderCodeFilter,
)
from hope_payment_gateway.api.western_union.serializers import (
    CorridorSerializer,
    ServiceProviderCodeSerializer,
)
from hope_payment_gateway.apps.core.grant import Grant
from hope_payment_gateway.apps.fsp.western_union.models import (
    Corridor,
    ServiceProviderCode,
)


class CorridorViewSet(ProtectedMixin, ModelViewSet, GrantRequiredTokenView):
    serializer_class = CorridorSerializer
    queryset = Corridor.objects.all()

    filterset_class = CorridorFilter
    search_fields = ["description"]
    write_grant = Grant.API_PLAN_MANAGE


class ServiceProviderCodeViewSet(ProtectedMixin, ModelViewSet, GrantRequiredTokenView):
    serializer_class = ServiceProviderCodeSerializer
    queryset = ServiceProviderCode.objects.all()

    filterset_class = ServiceProviderCodeFilter
    search_fields = ["description", "code"]
    write_grant = Grant.API_PLAN_MANAGE
