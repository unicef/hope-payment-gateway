from django_fsm import TransitionNotAllowed
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from hope_payment_gateway.api.western_union.filters import PaymentInstructionFilter, PaymentRecordLogFilter
from hope_payment_gateway.api.western_union.serializers import (
    PaymentInstructionSerializer,
    PaymentRecordLogLightSerializer,
    PaymentRecordLogSerializer,
)
from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecordLog


class LoggingAPIViewSet(viewsets.ModelViewSet):
    def destroy(self, request, pk=None):
        raise NotImplementedError


class PaymentInstructionViewSet(LoggingAPIViewSet):
    serializer_class = PaymentInstructionSerializer
    queryset = PaymentInstruction.objects.all()

    lookup_field = "uuid"
    filterset_class = PaymentInstructionFilter
    search_fields = ["unicef_id", "uuid"]

    def _change_status(self, status):
        instruction = self.get_object()
        try:
            transaction = getattr(instruction, status)
            transaction()
            instruction.save()
            return Response({"status": instruction.status})
        except TransitionNotAllowed as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)

    @action(detail=True)  # , methods=['post']
    def open(self, request, uuid=None):
        return self._change_status("open")

    @action(detail=True)  # , methods=['post']
    def ready(self, request, uuid=None):
        return self._change_status("ready")

    @action(detail=True)  # , methods=['post']
    def close(self, request, uuid=None):
        return self._change_status("close")

    @action(detail=True)  # , methods=['post']
    def cancel(self, request, uuid=None):
        return self._change_status("cancel")

    @action(detail=True, methods=["post"])
    def add_records(self, request, uuid=None):
        obj = self.get_object()
        if obj.status != PaymentInstruction.OPEN:
            Response(
                {"message": f"Cannot add records not a Open Plan", "status": obj.status}, status=HTTP_400_BAD_REQUEST
            )
        data = request.data.copy()
        for record in data:
            record["parent"] = obj.id
        serializer = PaymentRecordLogSerializer(data=data, many=True)
        if serializer.is_valid():
            totals = serializer.save()
            return Response(
                {"uuid": obj.uuid, "records": {item.record_code: item.uuid for item in totals}}, status=HTTP_201_CREATED
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class PaymentRecordLogViewSet(LoggingAPIViewSet):
    serializer_class = PaymentRecordLogSerializer
    queryset = PaymentRecordLog.objects.all()
    lookup_field = "uuid"
    filterset_class = PaymentRecordLogFilter
    search_fields = ("uuid", "record_code")

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentRecordLogLightSerializer
        return super().get_serializer_class()
