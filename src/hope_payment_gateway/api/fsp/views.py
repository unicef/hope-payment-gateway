from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_api_auth.views import LoggingAPIViewSet
from hope_payment_gateway.api.fsp.filters import (
    DeliveryMechanismFilter,
    ExportTemplateFilter,
    FinancialServiceProviderConfigFilter,
    FinancialServiceProviderFilter,
    PaymentInstructionFilter,
    PaymentRecordFilter,
)
from hope_payment_gateway.api.fsp.serializers import (
    DeliveryMechanismSerializer,
    ExportTemplateSerializer,
    FinancialServiceProviderConfigSerializer,
    FinancialServiceProviderSerializer,
    PaymentInstructionSerializer,
    PaymentRecordLightSerializer,
    PaymentRecordSerializer,
)
from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.actions import export_as_template_impl
from hope_payment_gateway.apps.gateway.flows import PaymentInstructionFlow
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    Office,
)


class ProtectedMixin:
    def destroy(self, request, pk=None):
        raise NotImplementedError


class DeliveryMechanismViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = DeliveryMechanismSerializer
    queryset = DeliveryMechanism.objects.all()

    filterset_class = DeliveryMechanismFilter
    search_fields = ["code", "name"]


class FinancialServiceProviderViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = FinancialServiceProviderSerializer
    queryset = FinancialServiceProvider.objects.prefetch_related("configs")

    filterset_class = FinancialServiceProviderFilter
    search_fields = ["name", "vendor_number", "remote_id"]


class ConfigurationViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = FinancialServiceProviderConfigSerializer
    queryset = FinancialServiceProviderConfig.objects.all()

    filterset_class = FinancialServiceProviderConfigFilter
    search_fields = ["description"]


class PaymentInstructionViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = PaymentInstructionSerializer
    queryset = PaymentInstruction.objects.all()

    lookup_field = "remote_id"
    filterset_class = PaymentInstructionFilter
    search_fields = ["external_code", "remote_id"]

    def perform_create(self, serializer) -> None:
        owner = get_user_model().objects.filter(apitoken=self.request.auth).first()
        system = System.objects.get(owner=owner)
        obj = serializer.save(system=system)
        config_key = obj.extra.get("config_key", None)
        if config_key:
            office, _ = Office.objects.get_or_create(
                code=config_key, defaults={"name": config_key, "slug": config_key, "supervised": True}
            )
            obj.office = office
            obj.save()

    def _change_status(self, status):
        instruction = self.get_object()
        try:
            flow = PaymentInstructionFlow(instruction)
            transaction = getattr(flow, status)
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
    def finalize(self, request, remote_id=None):
        return self._change_status("finalize")

    @action(detail=True, methods=["post"])
    def process(self, request, remote_id=None):
        return self._change_status("process")

    @action(detail=True, methods=["post"])
    def abort(self, request, remote_id=None):
        return self._change_status("abort")

    @action(detail=True, methods=["post"])
    def add_records(self, request, remote_id=None):
        obj = self.get_object()
        if obj.status != PaymentInstructionState.OPEN:
            return Response(
                {
                    "message": "Cannot add records to a not Open Plan",
                    "status": obj.status,
                },
                status=HTTP_400_BAD_REQUEST,
            )
        data = request.data.copy()
        for record in data:
            record["parent"] = obj.remote_id
        serializer = PaymentRecordSerializer(data=data, many=True)
        if serializer.is_valid():
            totals = serializer.save()
            return Response(
                {
                    "remote_id": obj.remote_id,
                    "records": {item.record_code: item.remote_id for item in totals},
                },
                status=HTTP_201_CREATED,
            )
        error_dict = {
            index: serializer.errors[index] for index in range(len(serializer.errors)) if serializer.errors[index]
        }
        return Response(
            {"remote_id": obj.remote_id, "errors": error_dict},
            status=HTTP_400_BAD_REQUEST,
        )

    @action(detail=True)  # , methods=["post"])
    def download(self, request, remote_id=None):
        obj = self.get_object()
        try:
            dm = DeliveryMechanism.objects.get(code=obj.extra.get("delivery_mechanism", None))
            export = ExportTemplate.objects.get(
                fsp=obj.fsp,
                config_key=obj.extra.get("config_key", None),
                delivery_mechanism=dm,
            )
            queryset = PaymentRecord.objects.select_related("parent__fsp").filter(parent=obj)

            return export_as_template_impl(
                queryset,
                export.query.split("\r\n"),
            )
        except ExportTemplate.DoesNotExist as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)


class PaymentRecordViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = PaymentRecordSerializer
    queryset = PaymentRecord.objects.select_related("parent")
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
            WesternUnionClient().refund(record.pk, dict)
            return Response({"message": "cancel triggered"})
        except TransitionNotAllowed as exc:
            return Response({"status_error": str(exc)}, status=HTTP_400_BAD_REQUEST)


class ExportTemplateViewSet(ProtectedMixin, LoggingAPIViewSet):
    serializer_class = ExportTemplateSerializer
    queryset = ExportTemplate.objects.select_related("fsp")
    filterset_class = ExportTemplateFilter
    search_fields = ("config_key",)
