import logging
from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Prefetch
from hope_api_auth.views import TokenRequiredView
from rest_framework import permissions as drf_permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet
from strategy_field.utils import fqn
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.api.fsp.filters import (
    AccountTypeFilter,
    DeliveryMechanismFilter,
    ExportTemplateFilter,
    FinancialServiceProviderConfigFilter,
    FinancialServiceProviderFilter,
    PaymentInstructionFilter,
    PaymentRecordFilter,
)
from hope_payment_gateway.api.fsp.serializers import (
    AccountTypeSerializer,
    DeliveryMechanismSerializer,
    ExportTemplateSerializer,
    FinancialServiceProviderConfigSerializer,
    FinancialServiceProviderSerializer,
    PaymentInstructionSerializer,
    PaymentRecordLightSerializer,
    PaymentRecordSerializer,
)
from hope_payment_gateway.api.western_union.client import WesternUnionClient
from hope_payment_gateway.apps.core.grant import Grant
from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.core.permissions import GrantPermission
from hope_payment_gateway.apps.gateway.actions import export_payment_instruction_to_email
from hope_payment_gateway.apps.gateway.flows import PaymentInstructionFlow
from hope_payment_gateway.apps.gateway.models import (
    AccountType,
    AsyncJob,
    Country,
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    Office,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
)

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.serializers import BaseSerializer


class GrantRequiredTokenView(TokenRequiredView):
    permission_classes = [GrantPermission]
    permission = Grant.API_READ_ONLY

    def get_permissions(self):
        # Override permission based on method
        if self.request.method in drf_permissions.SAFE_METHODS:
            self.permission = Grant.API_READ_ONLY
        else:
            # For write operations, determine based on action
            action = getattr(self, "action", None)
            if action in ["cancel", "open", "ready", "close", "finalize", "process", "abort", "destroy"]:
                self.permission = Grant.API_PLAN_MANAGE
            elif action in ["create", "update", "partial_update", "add_records"]:
                self.permission = Grant.API_PLAN_UPLOAD
            else:
                self.permission = Grant.API_PLAN_MANAGE
        return super().get_permissions()


logger = logging.getLogger(__name__)


class ProtectedMixin:
    def destroy(self, request: "Request", *args: Any, **kwargs: Any) -> Response:
        raise NotImplementedError


class AccountTypeViewSet(ProtectedMixin, ModelViewSet[AccountType], GrantRequiredTokenView):  # type: ignore[misc]
    serializer_class = AccountTypeSerializer
    queryset = AccountType.objects.all()

    filterset_class = AccountTypeFilter
    search_fields = ["key", "label"]


class DeliveryMechanismViewSet(ProtectedMixin, ModelViewSet[DeliveryMechanism], GrantRequiredTokenView):  # type: ignore[misc]
    serializer_class = DeliveryMechanismSerializer
    queryset = DeliveryMechanism.objects.select_related("account_type")

    filterset_class = DeliveryMechanismFilter
    search_fields = ["code", "name"]


class FinancialServiceProviderViewSet(
    ProtectedMixin,
    ModelViewSet[FinancialServiceProvider],
    GrantRequiredTokenView,  # type: ignore[misc]
):
    serializer_class = FinancialServiceProviderSerializer
    queryset = FinancialServiceProvider.objects.prefetch_related(
        Prefetch(
            "configs",
            queryset=FinancialServiceProviderConfig.objects.select_related(
                "country",
                "office",
                "delivery_mechanism",
            ),
        )
    )

    filterset_class = FinancialServiceProviderFilter
    search_fields = ["name", "vendor_number", "remote_id"]


class ConfigurationViewSet(
    ProtectedMixin,
    ModelViewSet[FinancialServiceProviderConfig],
    GrantRequiredTokenView,  # type: ignore[misc]
):
    serializer_class = FinancialServiceProviderConfigSerializer
    queryset = FinancialServiceProviderConfig.objects.select_related(
        "fsp",
        "delivery_mechanism",
        "office",
        "country",
    )

    filterset_class = FinancialServiceProviderConfigFilter
    search_fields = ["description"]


class PaymentInstructionViewSet(ProtectedMixin, ModelViewSet[PaymentInstruction], GrantRequiredTokenView):  # type: ignore[misc]
    serializer_class = PaymentInstructionSerializer
    queryset = PaymentInstruction.objects.select_related("fsp", "delivery_mechanism", "office", "country")

    lookup_field = "remote_id"
    filterset_class = PaymentInstructionFilter
    search_fields = ["external_code", "remote_id"]

    write_permission = Grant.API_PLAN_UPLOAD
    required_grant_for_action = {
        "update": Grant.API_PLAN_MANAGE,
        "partial_update": Grant.API_PLAN_MANAGE,
        "open": Grant.API_PLAN_MANAGE,
        "ready": Grant.API_PLAN_MANAGE,
        "close": Grant.API_PLAN_MANAGE,
        "finalize": Grant.API_PLAN_MANAGE,
        "process": Grant.API_PLAN_MANAGE,
        "abort": Grant.API_PLAN_MANAGE,
        "add_records": Grant.API_PLAN_UPLOAD,
    }

    def perform_create(self, serializer: "BaseSerializer[Any]") -> None:
        owner = self.request.user
        if not getattr(owner, "pk", None) or not isinstance(owner, AbstractBaseUser):
            raise PermissionDenied("Authenticated user is required")
        system = System.objects.get(owner_id=owner.pk)
        obj = serializer.save(system=system)
        config_key = obj.payload.get("config_key", None)
        obj.save()
        if config_key:
            office, _ = Office.objects.get_or_create(
                code=config_key,
                defaults={"name": config_key, "slug": config_key, "supervised": False},
            )
            obj.office = office
            if office.supervised:
                obj.active = False
            if ctr_code := obj.payload.get("destination_country"):
                country, _ = Country.objects.get_or_create(
                    iso_code2=ctr_code,
                )
                obj.country = country

            obj.save()

    def _change_status(self, status: str) -> Response:
        instruction = self.get_object()
        try:
            flow = PaymentInstructionFlow(instruction)
            transaction = getattr(flow, status)
            transaction()
            instruction.save()
            return Response({"status": instruction.status})
        except TransitionNotAllowed as exc:
            logger.warning("Transition not allowed: %s", exc)
            return Response(
                # codeql[py/stack-trace-exposure] intentional client-facing state error
                {"status_error": str(exc)},
                status=HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def open(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("open")

    @action(detail=True, methods=["post"])
    def ready(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("ready")

    @action(detail=True, methods=["post"])
    def close(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("close")

    @action(detail=True, methods=["post"])
    def finalize(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("finalize")

    @action(detail=True, methods=["post"])
    def process(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("process")

    @action(detail=True, methods=["post"])
    def abort(self, request: "Request", remote_id: str | None = None) -> Response:
        return self._change_status("abort")

    @action(detail=True, methods=["post"])
    def add_records(self, request: "Request", remote_id: str | None = None) -> Response:
        obj = self.get_object()
        if obj.status != PaymentInstructionState.OPEN:
            return Response(
                {
                    "message": "Cannot add records to a not Open Plan",
                    "status": obj.status,
                },
                status=HTTP_400_BAD_REQUEST,
            )
        data = cast("list[dict[str, Any]]", request.data.copy())
        for record in data:
            record["parent"] = obj.remote_id
        serializer = PaymentRecordSerializer(data=data, many=True)
        if serializer.is_valid():
            # `many=True` builds a `ListSerializer` at runtime, which the DRF
            # stubs do not model, so `save()` is reported as a single instance.
            totals = cast("list[PaymentRecord]", serializer.save())
            return Response(
                {
                    "remote_id": obj.remote_id,
                    "records": {item.record_code: item.remote_id for item in totals},
                },
                status=HTTP_201_CREATED,
            )
        errors = serializer.errors
        if isinstance(errors, list):
            error_dict = {str(i): v for i, v in enumerate(errors) if v}
        else:
            error_dict = {k: v for k, v in errors.items() if v}
        return Response(
            {"remote_id": obj.remote_id, "errors": error_dict},
            status=HTTP_400_BAD_REQUEST,
        )

    @action(detail=True)  # , methods=["post"])
    def download(self, request: "Request", remote_id: str | None = None) -> Response:
        obj = self.get_object()
        export = obj.selected_export
        if not export:
            return Response({"status_error": "No template found"}, status=HTTP_400_BAD_REQUEST)

        user = request.user
        if not getattr(user, "is_authenticated", False) or not getattr(user, "email", None):
            return Response({"status_error": "User email is required"}, status=HTTP_400_BAD_REQUEST)

        job = AsyncJob.objects.create(
            description="Payment instruction export",
            type=AsyncJob.JobType.STANDARD_TASK,
            owner=user,
            instruction=obj,
            action=fqn(export_payment_instruction_to_email),
            config={"payment_instruction_id": obj.pk, "send_to": user.email},
        )
        job.queue()
        return Response(
            {"message": "Export scheduled", "job_id": job.pk},
            status=HTTP_202_ACCEPTED,
        )


class PaymentRecordViewSet(ProtectedMixin, ModelViewSet[PaymentRecord], GrantRequiredTokenView):  # type: ignore[misc]
    serializer_class = PaymentRecordSerializer
    queryset = PaymentRecord.objects.select_related("parent")
    lookup_field = "remote_id"
    filterset_class = PaymentRecordFilter
    search_fields = ("remote_id", "record_code")

    write_permission = Grant.API_PLAN_UPLOAD
    required_grant_for_action = {
        "update": Grant.API_PLAN_MANAGE,
        "partial_update": Grant.API_PLAN_MANAGE,
        "cancel": Grant.API_PLAN_MANAGE,
    }

    def get_serializer_class(self) -> "type[BaseSerializer[Any]]":
        if self.action == "list":
            return PaymentRecordLightSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["post"])
    def cancel(self, request: "Request", **kwargs: Any) -> Response:
        record = self.get_object()
        try:
            WesternUnionClient().refund(record.fsp_code, record.get_payload())
            return Response({"message": "cancel triggered"})
        except TransitionNotAllowed as exc:
            logger.warning("Transition not allowed: %s", exc)
            return Response(
                # codeql[py/stack-trace-exposure] intentional client-facing state error
                {"status_error": str(exc)},
                status=HTTP_400_BAD_REQUEST,
            )


class ExportTemplateViewSet(ProtectedMixin, ModelViewSet[ExportTemplate], GrantRequiredTokenView):  # type: ignore[misc]
    serializer_class = ExportTemplateSerializer
    queryset = ExportTemplate.objects.select_related("fsp")
    filterset_class = ExportTemplateFilter
    search_fields = ("config_key",)
