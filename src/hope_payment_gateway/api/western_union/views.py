from rest_framework.viewsets import ModelViewSet

from hope_payment_gateway.api.western_union.filters import CorridorFilter
from hope_payment_gateway.api.western_union.serializers import CorridorSerializer
from hope_payment_gateway.apps.fsp.western_union.models import Corridor


class ProtectedMixin:
    def destroy(self, request, pk=None):
        raise NotImplementedError


class CorridorViewSet(ProtectedMixin, ModelViewSet):
    serializer_class = CorridorSerializer
    queryset = Corridor.objects.all()

    filterset_class = CorridorFilter
    search_fields = ["description"]
