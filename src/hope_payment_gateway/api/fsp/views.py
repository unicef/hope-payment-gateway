from django.contrib.auth import get_user_model

from django_fsm import TransitionNotAllowed
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from hope_api_auth.views import LoggingAPIViewSet
from hope_payment_gateway.api.fsp.filters import (
    FinancialServiceProviderFilter,
    PaymentInstructionFilter,
    PaymentRecordFilter,
)
from hope_payment_gateway.api.fsp.serializers import (
    FinancialServiceProviderSerializer,
    PaymentInstructionSerializer,
    PaymentRecordLightSerializer,
    PaymentRecordSerializer,
)
from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.fsp.western_union.endpoints.cancel import cancel
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord


class ProtectedMixin:
    def destroy(self, request, pk=None):
        raise NotImplementedError


class FinancialServiceProviderViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = FinancialServiceProviderSerializer
    queryset = FinancialServiceProvider.objects.all()

    filterset_class = FinancialServiceProviderFilter
    search_fields = ["name", "vision_vendor_number", "remote_id"]


class PaymentInstructionViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = PaymentInstructionSerializer
    queryset = PaymentInstruction.objects.all()

    lookup_field = "remote_id"
    filterset_class = PaymentInstructionFilter
    search_fields = ["unicef_id", "remote_id"]

    def perform_create(self, serializer):
        try:
            owner = get_user_model().objects.get(apitoken=self.request.auth)
            system = System.objects.get(owner=owner)
        except System.DoesNotExist as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)
        serializer.save(system=system)

    def _change_status(self, status):
        instruction = self.get_object()
        try:
            transaction = getattr(instruction, status)
            transaction()
            instruction.save()
            return Response({"status": instruction.status})
        except TransitionNotAllowed as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def open(self, request, remote_id=None):
        return self._change_status("open")

    @action(detail=True, methods=["post"])
    def ready(self, request, remote_id=None):
        return self._change_status("ready")

    @action(detail=True, methods=["post"])
    def close(self, request, remote_id=None):
        return self._change_status("close")

    @action(detail=True, methods=["post"])
    def process(self, request, remote_id=None):
        return self._change_status("process")

    @action(detail=True, methods=["post"])
    def abort(self, request, remote_id=None):
        return self._change_status("abort")

    @action(detail=True, methods=["post"])
    def add_records(self, request, remote_id=None):
        obj = self.get_object()
        if obj.status != PaymentInstruction.OPEN:
            return Response(
                {"message": "Cannot add records to a not Open Plan", "status": obj.status}, status=HTTP_400_BAD_REQUEST
            )
        data = request.data.copy()
        for record in data:
            record["parent"] = obj.remote_id
        serializer = PaymentRecordSerializer(data=data, many=True)
        if serializer.is_valid():
            totals = serializer.save()
            return Response(
                {"remote_id": obj.remote_id, "records": {item.record_code: item.remote_id for item in totals}},
                status=HTTP_201_CREATED,
            )
        error_dict = {
            index: serializer.errors[index] for index in range(len(serializer.errors)) if serializer.errors[index]
        }
        return Response({"remote_id": obj.remote_id, "errors": error_dict}, status=HTTP_400_BAD_REQUEST)


class PaymentRecordViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = PaymentRecordSerializer
    queryset = PaymentRecord.objects.all()
    lookup_field = "remote_id"
    filterset_class = PaymentRecordFilter
    search_fields = ("remote_id", "record_code")

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentRecordLightSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["post"])
    def cancel(self, request):
        record = self.get_object()
        try:
            cancel(record.pk)
            return Response({"message": "cancel triggered"})
        except TransitionNotAllowed as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)
