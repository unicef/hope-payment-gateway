import csv
import logging
from typing import TYPE_CHECKING, Optional, Union

from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.db.models import JSONField
from django.db.utils import IntegrityError
from django.forms import FileField, FileInput, Form
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from admin_extra_buttons.decorators import button, choice, link, view
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminactions.export import base_export
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from jsoneditor.forms import JSONEditor
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.moneygram.client import InvalidToken, MoneyGramClient, PayloadMissingKey
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.exceptions import InvalidCorridor, PayloadException
from hope_payment_gateway.apps.gateway.actions import TemplateExportForm, export_as_template, export_as_template_impl
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponseRedirect


logger = logging.getLogger(__name__)


class ImportCSVForm(Form):
    file = FileField(widget=FileInput(attrs={"accept": "text/csv"}))


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_display = (
        "record_code",
        "fsp_code",
        "parent",
        "status",
        "message",
        "success",
        "remote_id",
        "auth_code",
        "payout_amount",
        "marked_for_payment",
    )
    list_filter = (
        ("parent", AutoCompleteFilter),
        "status",
        "success",
    )
    search_fields = ("record_code", "fsp_code", "auth_code", "message")
    readonly_fields = ("extra_data",)
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }

    actions = [export_as_template]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent__fsp")

    @choice(change_list=False)
    def western_union(self, button):
        button.choices = [
            self.wu_prepare_payload,
            self.wu_send_money_validation,
            self.wu_send_money,
            self.wu_search_request,
            self.wu_cancel,
        ]
        return button

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Prepare Payload")
    def wu_prepare_payload(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        payload = obj.get_payload()
        try:
            payload = WesternUnionClient.create_validation_payload(payload)
            client = WesternUnionClient()
            _, data = client.prepare(client.quote_client, "sendmoneyValidation", payload)

            context["title"] = "Western Union Payload"
            context["content"] = data
            return TemplateResponse(request, "request.html", context)

        except (PayloadException, InvalidCorridor, PayloadMissingKey) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Send Money Validation")
    def wu_send_money_validation(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        payload = obj.get_payload()
        context["msg"] = "First call: check if data is valid \n it returns MTCN"
        try:
            payload = WesternUnionClient.create_validation_payload(payload)
            context.update(WesternUnionClient().send_money_validation(payload))
            return TemplateResponse(request, "request.html", context)
        except (PayloadException, InvalidCorridor) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Send Money")
    def wu_send_money(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        client = WesternUnionClient()
        log = client.create_transaction(obj.get_payload())
        if log is None:
            messages.add_message(request, messages.ERROR, "Invalid record: Invalid status")
        else:
            loglevel = messages.SUCCESS if log.success else messages.ERROR
            messages.add_message(request, loglevel, log.message)

    @view(html_attrs={"style": "background-color:yellow;color:blue"}, label="Search Request")
    def wu_search_request(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["msg"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
            frm = obj.extra_data.get("foreign_remote_system", None)
            context.update(WesternUnionClient().search_request(frm, mtcn))
            return TemplateResponse(request, "request.html", context)
        messages.warning(request, "Missing MTCN")

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Cancel")
    def wu_cancel(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["obj"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
        log = WesternUnionClient().refund(obj.fsp_code, obj.extra_data)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Prepare Payload")
    def mg_prepare_payload(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            client = MoneyGramClient()
            title, content = client.prepare_transaction(obj.get_payload())
            context["title"] = f"MoneyGram Payload: {title}"
            context["format"] = "json"
            context["content"] = content
            return TemplateResponse(request, "request.html", context)

        except (PayloadException, InvalidCorridor, PayloadMissingKey) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return obj
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Create Transaction")
    def mg_create_transaction(self, request, pk) -> TemplateResponse:

        obj = PaymentRecord.objects.get(pk=pk)
        try:
            client = MoneyGramClient()
            resp = client.create_transaction(obj.get_payload())
            return self.handle_mg_response(request, resp, pk, "Create Transaction")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Quote")
    def mg_quote_transaction(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().quote(obj.get_payload())
            return self.handle_mg_response(request, resp, pk, "Quote Transaction")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Status")
    def mg_status(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().query_status(obj.fsp_code, update=False)
            return self.handle_mg_response(request, resp, pk, "Status")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Status Update")
    def mg_status_update(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().query_status(obj.fsp_code, update=True)
            return self.handle_mg_response(request, resp, pk, "Status + Update")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)
        except TransitionNotAllowed as e:
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Required Fields")
    def mg_get_required_fields(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().get_required_fields(obj.get_payload())
            return self.handle_mg_response(request, resp, pk, "Required Fields")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Service Options")
    def mg_get_service_options(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().get_service_options(obj.get_payload())
            return self.handle_mg_response(request, resp, pk, "Service Options")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"}, label="Refund")
    def mg_refund(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            resp = MoneyGramClient().refund(obj.fsp_code, obj.get_payload())
            return self.handle_mg_response(request, resp, pk, "Refund")
        except InvalidToken as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @choice(change_list=False)
    def moneygram(self, button):
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
        return button

    @link()
    def instruction(self, button: button) -> Optional[str]:
        if "original" in button.context:
            obj = button.context["original"]
            button.href = reverse("admin:gateway_paymentinstruction_change", args=[obj.parent.pk])
            button.visible = True
        else:
            button.visible = False
        return None

    def handle_mg_response(self, request, resp, pk, title):
        if resp:
            data = resp.data
            msgs = []
            if resp.status_code == 200:
                context = self.get_common_context(request, pk)
                context["title"] = title
                context["format"] = "json"
                context["content"] = data
                return TemplateResponse(request, "request.html", context)

            elif 400 <= resp.status_code < 500:
                loglevel = messages.WARNING
                if "errors" in data:
                    for error in data["errors"]:
                        msgs.append(f"{error['message']} ({error['code']})")
                        if "offendingFields" in error:
                            for field in error["offendingFields"]:
                                if "field" in field:
                                    msgs.append(f"Field: {field['field']}")
                elif "error" in data:
                    message = data.get("message", data["error"])
                    msgs.append(message)
                else:
                    msgs = [
                        "Error",
                    ]
            else:
                loglevel = messages.ERROR
                errors = dict()
                if "errors" in data:
                    errors = data["errors"]
                if "error" in data:
                    errors = data["error"]
                if isinstance(errors, list):
                    for error in errors:
                        msgs.append(f"{error['message']} ({error['code']})")
                else:
                    msgs.append(f"{errors['message']} ({errors['code']})")
            for msg in msgs:
                messages.add_message(request, loglevel, msg)
        else:
            messages.add_message(request, messages.ERROR, "Connection Error")


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("external_code", "status", "remote_id")
    list_filter = ("status",)
    search_fields = ("external_code",)
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    # readonly_fields = ("extra",)

    @button()
    def export(self, request, pk) -> TemplateResponse:
        obj = self.get_object(request, str(pk))
        queryset = PaymentRecord.objects.select_related("parent__fsp").filter(parent=obj)

        # hack to use the action
        post_dict = request.POST.copy()
        post_dict["action"] = 0
        post_dict["_selected_action"] = list()
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

    @button()
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
                            if key in ["first_name", "last_name", "amount", "phone_no", "service_provider_code"]
                        }
                        PaymentRecord.objects.create(
                            record_code=row["record_code"], remote_id=row["record_code"], parent=parent, payload=payload
                        )
                        n += 1

                    self.message_user(request, f"Uploaded {n} records {instruction}")

                    return redirect("admin:gateway_paymentinstruction_change", object_id=pk)
                except IntegrityError as e:
                    logger.error(e)
                    self.message_user(request, str(e), messages.ERROR)
                except Exception as e:
                    logger.error(e)
                    self.message_user(request, "Unable to parse the file, please check the format", messages.ERROR)
        else:
            form = ImportCSVForm()
        context["form"] = form
        return TemplateResponse(request, "admin/gateway/import_records_csv.html", context)

    @link()
    def records(self, button: button) -> Optional[str]:
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


@admin.register(DeliveryMechanism)
class DeliveryMechanismAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("code", "name", "transfer_type")
    search_fields = ("code", "name")
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }


@admin.register(ExportTemplate)
class ExportTemplateAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("fsp", "config_key", "delivery_mechanism")
    search_fields = ("config_key", "delivery_mechanism__name")
