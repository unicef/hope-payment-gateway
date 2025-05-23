from django.http import FileResponse
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from hope_payment_gateway.api.western_union.filters import (
    CorridorFilter,
    ServiceProviderCodeFilter,
)
from hope_payment_gateway.api.western_union.serializers import (
    CorridorSerializer,
    FileSerializer,
    ServiceProviderCodeSerializer,
)
from hope_payment_gateway.apps.fsp.western_union.models import (
    Corridor,
    ServiceProviderCode,
)
from hope_payment_gateway.libs.ftp import FTPClient


class ProtectedMixin:
    def destroy(self, request, pk=None):
        raise NotImplementedError


class CorridorViewSet(ProtectedMixin, ModelViewSet):
    serializer_class = CorridorSerializer
    queryset = Corridor.objects.all()

    filterset_class = CorridorFilter
    search_fields = ["description"]


class ServiceProviderCodeViewSet(ProtectedMixin, ModelViewSet):
    serializer_class = ServiceProviderCodeSerializer
    queryset = ServiceProviderCode.objects.all()

    filterset_class = ServiceProviderCodeFilter
    search_fields = ["description", "code"]


class FileViewset(ViewSet):
    serializer_class = FileSerializer
    lookup_field = "filename"
    lookup_value_regex = r".*\..*"
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        return FTPClient().ls()

    def list(self, request):
        serializer = self.serializer_class(instance=self.get_queryset(), many=True, context={"request": request})
        return Response(serializer.data)

    def retrieve(self, request, filename=None):
        try:
            response = FileResponse(FTPClient().download(filename))
        except FileNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
        return response
