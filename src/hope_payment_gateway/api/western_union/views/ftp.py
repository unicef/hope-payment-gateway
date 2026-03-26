import socket

from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from hope_payment_gateway.api.western_union.serializers import (
    FileSerializer,
)
from hope_payment_gateway.apps.core.permissions import HasAnyPermission
from hope_payment_gateway.libs.ftp import FTPClient


class FileViewset(ViewSet):
    serializer_class = FileSerializer
    lookup_field = "filename"
    lookup_value_regex = r".*\..*"

    permission_classes = (HasAnyPermission,)
    required_permissions = ["core.can_access_ftp"]

    def get_queryset(self):
        return FTPClient().ls()

    def list(self, request):
        try:
            serializer = self.serializer_class(instance=self.get_queryset(), many=True, context={"request": request})
        except socket.gaierror:
            return Response(
                {"context": [{"code": "ftp_error", "message": "cannot reach FTP server"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializer.data)

    def retrieve(self, request, filename=None):
        try:
            response = FileResponse(FTPClient().download(filename))
        except FileNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
        return response
