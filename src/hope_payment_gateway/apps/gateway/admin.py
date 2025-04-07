import csv
import logging
from typing import TYPE_CHECKING, Union

from admin_extra_buttons.decorators import button, choice, link, view
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminactions.export import base_export
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from constance import config
from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.db.models import JSONField, QuerySet
from django.db.utils import IntegrityError
from django.forms import FileField, FileInput, Form
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django_celery_boost.admin import CeleryTaskModelAdmin
from jsoneditor.forms import JSONEditor
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.moneygram.client import InvalidTokenError, MoneyGramClient, PayloadMissingKeyError
from hope_payment_gateway.apps.fsp.utils import extrapolate_errors
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.exceptions import InvalidCorridorError, PayloadException
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.actions import (
    TemplateExportForm,
    export_as_template,
    export_as_template_impl,
    moneygram_refund,
    moneygram_update_status,
)
from hope_payment_gateway.apps.gateway.models import (
    AsyncJob,
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
    Office,
    AccountType,
)

if TYPE_CHECKING:
    from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect


logger = logging.getLogger(__name__)


class ImportCSVForm(Form):
    file = FileField(widget=FileInput(attrs={"accept": "text/csv"}))


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_display = (
        "record_code",
        "fsp",
        "parent",
        "status",
        "message",
        "success",
        "remote_id",
        "payout_amount",
        "payout_date",
        "fsp_code",
        "auth_code",
    )
    list_filter = ("parent__fsp", ("parent", AutoCompleteFilter), "status", "success")
    search_fields = ("remote_id", "record_code", "fsp_code", "auth_code", "message")
    readonly_fields = ("extra_data",)
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    raw_id_fields = ("parent",)

    actions = [export_as_template, moneygram_update_status, moneygram_refund]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("parent__fsp")

    def fsp(self, obj: PaymentRecord) -> str:
        return obj.parent.fsp.name

    @choice(change_list=False, label="Western Union")
    def western_union(self, button):
        obj: PaymentRecord = button.original

        if obj.parent.fsp.vendor_number == config.WESTERN_UNION_VENDOR_NUMBER:
            button.choices = [
                self.wu_prepare_payload,
                self.wu_send_money_validation,
                self.wu_send_money,
                self.wu_status,
                self.wu_status_update,
                self.wu_search_request,
                self.wu_cancel,
            ]
            payload = obj.get_payload()
            if (
                Corridor.objects.filter(
                    destination_country=payload.get("destination_country"),
                    destination_currency=payload.get("destination_currency"),
                ).exists()
                and payload.get("delivery_services_code") == "800"
            ):
                button.choices.append(self.wu_corridor)
            if obj.parent.fsp.configs.filter(
                key=obj.parent.extra.get("config_key"), delivery_mechanism=payload.get("delivery_mechanism")
            ).first():
                button.choices.append(self.wu_config)
        else:
            button.visible = False
        return button

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Prepare Payload",
        permission="western_union.can_prepare_transaction",
    )
    def wu_prepare_payload(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        payload = obj.get_payload()
        try:
            payload = WesternUnionClient.create_validation_payload(payload)
            client = WesternUnionClient()
            _, data = client.prepare(client.quote_client, "sendmoneyValidation", payload)

            context["title"] = "Western Union Payload"
            context["content_request"] = payload
            context["content_response"] = data
            return TemplateResponse(request, "request.html", context)

        except (PayloadException, InvalidCorridorError, PayloadMissingKeyError) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Send Money Validation",
        permission="western_union.can_prepare_transaction",
    )
    def wu_send_money_validation(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        payload = obj.get_payload()
        context["msg"] = "First call: check if data is valid \n it returns MTCN"
        try:
            payload = WesternUnionClient.create_validation_payload(payload)
            context.update(WesternUnionClient().send_money_validation(payload))
            return TemplateResponse(request, "request.html", context)
        except (PayloadException, InvalidCorridorError) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Send Money",
        permission="western_union.can_create_transaction",
    )
    def wu_send_money(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        client = WesternUnionClient()
        log = client.create_transaction(obj.get_payload())
        if log is None:
            messages.add_message(request, messages.ERROR, "Invalid record: Invalid status")
        else:
            loglevel = messages.SUCCESS if log.success else messages.ERROR
            messages.add_message(request, loglevel, log.message)

    @view(
        html_attrs={"style": "background-color:yellow;color:blue"},
        label="Check Status",
        permission="western_union.can_check_status",
    )
    def wu_status(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.auth_code:
            context["msg"] = f"Search request through MTCN \nPARAM: mtcn {mtcn}"
            context.update(WesternUnionClient().query_status(obj.fsp_code, False))
        else:
            messages.warning(request, "Missing MTCN")
        return TemplateResponse(request, "request.html", context)

    @view(
        html_attrs={"style": "background-color:yellow;color:blue"},
        label="Status Update",
        permission="western_union.can_update_status",
    )
    def wu_status_update(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.auth_code:
            context["msg"] = f"Search request through MTCN \nPARAM: mtcn {mtcn}"
            context.update(WesternUnionClient().query_status(obj.fsp_code, True))
        else:
            messages.warning(request, "Missing MTCN")
        return TemplateResponse(request, "request.html", context)

    @view(
        html_attrs={"style": "background-color:yellow;color:blue"},
        label="Search Request",
        permission="western_union.can_search_request",
    )
    def wu_search_request(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.auth_code:
            context["msg"] = f"Search request through MTCN \nPARAM: mtcn {mtcn}"
            frm = obj.extra_data.get("foreign_remote_system", None)
            context.update(WesternUnionClient().search_request(frm, mtcn))
        else:
            messages.warning(request, "Missing MTCN")
        return TemplateResponse(request, "request.html", context)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Cancel",
        permission="western_union.can_cancel_transaction",
    )
    def wu_cancel(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.auth_code:
            context["obj"] = f"Search request through MTCN \nPARAM: mtcn {mtcn}"
        log = WesternUnionClient().refund(obj.fsp_code, obj.extra_data)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Corridor",
    )
    def wu_corridor(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = self.get_object(request, pk)
        payload = obj.get_payload()

        corridor = Corridor.objects.get(
            destination_country=payload.get("destination_country"),
            destination_currency=payload.get("destination_currency"),
        )
        return redirect(reverse("admin:western_union_corridor_change", args=[corridor.pk]))

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Config",
    )
    def wu_config(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = self.get_object(request, pk)
        config = obj.parent.fsp.configs.get(key=obj.parent.extra.get("config_key"))
        return redirect(reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk]))

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Prepare Payload",
        permissions="moneygram.can_prepare_transaction",
    )
    def mg_prepare_payload(self, request: HttpRequest, pk: int) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            client = MoneyGramClient()
            title, content = client.prepare_transaction(obj.get_payload())
            context["title"] = f"MoneyGram Payload: {title}"
            context["format"] = "json"
            context["content_response"] = content
            return TemplateResponse(request, "request.html", context)

        except (PayloadException, InvalidCorridorError, PayloadMissingKeyError) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Create Transaction",
        permission="moneygram.can_create_transaction",
    )
    def mg_create_transaction(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            client = MoneyGramClient()
            try:
                payload, resp = client.create_transaction(obj.get_payload())
                return self.handle_mg_response(request, payload, resp, pk, "Create Transaction")
            except KeyError as e:
                self.message_user(request, f"Keyerror: {str(e)}", messages.ERROR)
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Quote",
        permissions="moneygram.can_quote_transaction",
    )
    def mg_quote_transaction(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            payload, resp = MoneyGramClient().quote(obj.get_payload())
            return self.handle_mg_response(request, payload, resp, pk, "Quote Transaction")
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)
        return reverse("admin:gateway_paymentrecord_change", args=[obj.pk])

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Status",
        permission="moneygram.can_check_status",
    )
    def mg_status(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        if obj.fsp_code:
            try:
                payload, resp = MoneyGramClient().query_status(
                    obj.fsp_code, obj.get_payload()["agent_partner_id"], update=False
                )
                return self.handle_mg_response(request, payload, resp, pk, "Status")
            except InvalidTokenError as e:
                logger.error(e)
                self.message_user(request, str(e), messages.ERROR)
        else:
            self.message_user(request, "Missing transaction ID", messages.WARNING)
        return reverse("admin:gateway_paymentrecord_change", args=[obj.pk])

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Status Update",
        permission="moneygram.can_update_status",
    )
    def mg_status_update(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        if obj.fsp_code:
            try:
                payload, resp = MoneyGramClient().query_status(
                    obj.fsp_code, obj.get_payload()["agent_partner_id"], update=True
                )
                return self.handle_mg_response(request, payload, resp, pk, "Status + Update")
            except InvalidTokenError as e:
                logger.error(e)
                self.message_user(request, str(e), messages.ERROR)
            except TransitionNotAllowed as e:
                self.message_user(request, str(e), messages.ERROR)
        else:
            self.message_user(request, "Missing transaction ID", messages.WARNING)
        return reverse("admin:gateway_paymentrecord_change", args=[obj.pk])

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Required Fields",
        permission="moneygram.can_quote_transaction",
    )
    def mg_get_required_fields(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            payload, resp = MoneyGramClient().get_required_fields(obj.get_payload())
            return self.handle_mg_response(request, payload, resp, pk, "Required Fields")
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Service Options",
        permission="moneygram.can_quote_transaction",
    )
    def mg_get_service_options(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            payload, resp = MoneyGramClient().get_service_options(obj.get_payload())
            return self.handle_mg_response(request, payload, resp, pk, "Service Options")
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Refund",
        permission="moneygram.can_cancel_transaction",
    )
    def mg_refund(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            payload, resp = MoneyGramClient().refund(obj.fsp_code, obj.get_payload())
            return self.handle_mg_response(request, payload, resp, pk, "Refund")
        except (InvalidTokenError, KeyError) as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @choice(change_list=False, label="MoneyGram")
    def moneygram(self, button):
        obj: PaymentRecord = button.original
        if obj.parent.fsp.vendor_number == config.MONEYGRAM_VENDOR_NUMBER:
            button.choices = [
                self.mg_prepare_payload,
                self.mg_create_transaction,
                self.mg_quote_transaction,
                self.mg_status,
                self.mg_status_update,
                self.mg_get_service_options,
                self.mg_get_required_fields,
                self.mg_refund,
            ]
        else:
            button.visible = False
        return button

    def handle_mg_response(
        self, request: HttpRequest, payload: dict, resp: HttpRequest, pk: int, title: str
    ) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        if resp:
            if resp.status_code < 300:
                context["title"] = title
                context["format"] = "json"
                context["content_request"] = payload
                context["content_response"] = resp.data
                return TemplateResponse(request, "request.html", context)

            loglevel, msgs = self.handle_error(resp)

            for msg in msgs:
                messages.add_message(request, loglevel, msg)
        else:
            messages.add_message(request, messages.ERROR, "Connection Error")
        return TemplateResponse(request, "request.html", context)

    def handle_error(self, resp) -> tuple:
        data = resp.data
        loglevel = messages.WARNING if resp.status_code < 500 else messages.ERROR
        msgs = extrapolate_errors(data)
        return loglevel, msgs


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("external_code", "office", "remote_id", "fsp", "status", "active", "tag")
    list_filter = ("fsp", "status", "active")
    search_fields = ("external_code", "remote_id", "fsp__name", "tag")
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    raw_id_fields = ("fsp", "system", "office")

    @button(permission="gateway.can_export_records")
    def export_records(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = self.get_object(request, str(pk))
        queryset = PaymentRecord.objects.select_related("parent__fsp").filter(parent=obj)

        # hack to use the action
        post_dict = request.POST.copy()
        post_dict["action"] = 0
        post_dict["_selected_action"] = list
        post_dict["select_across"] = "0"

        request.POST = post_dict

        return base_export(
            self,
            request,
            queryset,
            name=export_as_template.short_description,
            impl=export_as_template_impl,
            title=export_as_template.short_description.capitalize(),
            action_short_description=export_as_template.short_description,
            template="payment_instruction/export.html",
            form_class=TemplateExportForm,
        )

    @button(permission="gateway.can_import_records")
    def import_records(
        self, request: "HttpRequest", pk: int
    ) -> Union["HttpResponsePermanentRedirect", "HttpResponseRedirect", TemplateResponse]:
        context = self.get_common_context(request, processed=False)
        if request.method == "POST":
            form = ImportCSVForm(data=request.POST, files=request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["file"]
                data_set = csv_file.read().decode("utf-8-sig").splitlines()
                reader = csv.DictReader(data_set)
                try:
                    instruction = None

                    n = 0
                    for row in reader:
                        parent = self.model.objects.get(pk=pk)
                        payload = {
                            key: row[key]
                            for key, value in row.items()
                            if key
                            in [
                                "first_name",
                                "last_name",
                                "amount",
                                "phone_no",
                                "service_provider_code",
                            ]
                        }
                        PaymentRecord.objects.create(
                            record_code=row["record_code"],
                            remote_id=row["record_code"],
                            parent=parent,
                            payload=payload,
                        )
                        n += 1

                    self.message_user(request, f"Uploaded {n} records {instruction}")

                    return redirect("admin:gateway_paymentinstruction_change", object_id=pk)
                except IntegrityError as e:
                    logger.error(e)
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = ImportCSVForm()
        context["form"] = form
        return TemplateResponse(request, "admin/gateway/import_records_csv.html", context)

    @link()
    def records(self, button: button) -> str | None:
        if "original" in button.context:
            obj = button.context["original"]
            url = reverse("admin:gateway_paymentrecord_changelist")
            button.href = f"{url}?parent={obj.pk}"
            button.visible = True
        else:
            button.visible = False
        return None


class FinancialServiceProviderConfigInline(TabularInline):
    model = FinancialServiceProviderConfig
    extra = 1


@admin.register(Office)
class OfficeAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("name", "long_name", "slug", "code", "supervised")
    search_fields = ("name", "slug", "code")
    list_filter = ("supervised",)
    readonly_fields = ("remote_id", "slug")
    ordering = ("name",)


@admin.register(FinancialServiceProvider)
class FinancialServiceProviderAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "vendor_number",
        "remote_id",
    )
    search_fields = ("remote_id", "name", "vendor_number")
    inlines = (FinancialServiceProviderConfigInline,)
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }


@admin.register(FinancialServiceProviderConfig)
class FinancialServiceProviderConfigAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("key", "office", "label", "fsp", "delivery_mechanism", "required_fields")
    search_fields = ("remote_id", "fsp__name", "delivery_mechanism__name", "delivery_mechanism__code")


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ("key", "label")
    search_fields = ("key", "label")


@admin.register(DeliveryMechanism)
class DeliveryMechanismAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("code", "name", "transfer_type", "account_type")
    search_fields = ("code", "name")
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    list_filter = ("transfer_type",)


@admin.register(ExportTemplate)
class ExportTemplateAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("fsp", "delivery_mechanism", "config_key")
    search_fields = ("config_key", "delivery_mechanism__name", "fsp__name")
    raw_id_fields = ("fsp", "delivery_mechanism")


@admin.register(AsyncJob)
class AsyncJobAdmin(AdminFiltersMixin, CeleryTaskModelAdmin, admin.ModelAdmin):
    list_display = ("type", "verbose_status", "owner")
    autocomplete_fields = ("owner", "content_type")
    list_filter = (
        ("owner", AutoCompleteFilter),
        "type",
    )

    def get_readonly_fields(self, request: "HttpRequest", obj: AsyncJob | None = None):
        if obj:
            return ("owner", "local_status", "type", "action", "sentry_id")
        return super().get_readonly_fields(request, obj)
