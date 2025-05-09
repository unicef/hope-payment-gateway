import csv
import logging
from typing import TYPE_CHECKING, Union
from django.http import HttpRequest, HttpResponseRedirect
from admin_extra_buttons.decorators import button, link, view
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminactions.export import base_export
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.db.models import JSONField, QuerySet
from django.db.utils import IntegrityError
from django.forms import FileField, FileInput, Form
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django_celery_boost.admin import CeleryTaskModelAdmin
from jsoneditor.forms import JSONEditor

from hope_payment_gateway.apps.fsp.utils import extrapolate_errors
from hope_payment_gateway.apps.gateway.actions import (
    TemplateExportForm,
    export_as_template,
    export_as_template_impl,
    moneygram_refund,
    moneygram_update_status,
)
from hope_payment_gateway.apps.gateway.admin.moneygram import MoneyGramAdminMixin
from hope_payment_gateway.apps.gateway.admin.palpay import PalPayAdminMixin
from hope_payment_gateway.apps.gateway.admin.western_union import WesternUnionAdminMixin
from hope_payment_gateway.apps.gateway.models import (
    AccountType,
    AsyncJob,
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    Office,
    PaymentInstruction,
    PaymentRecord,
    Country,
)

if TYPE_CHECKING:
    from django.http import HttpResponsePermanentRedirect  # pragma: no-cover


logger = logging.getLogger(__name__)


class ImportCSVForm(Form):
    file = FileField(widget=FileInput(attrs={"accept": "text/csv"}))


@admin.register(PaymentRecord)
class PaymentRecordAdmin(
    PalPayAdminMixin,
    MoneyGramAdminMixin,
    WesternUnionAdminMixin,
    ExtraButtonsMixin,
    AdminFiltersMixin,
    admin.ModelAdmin,
):
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

    def handle_error(self, resp) -> tuple:
        data = resp.data
        loglevel = messages.WARNING if resp.status_code < 500 else messages.ERROR
        msgs = extrapolate_errors(data)
        return loglevel, msgs

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Config",
    )
    def configuration(self, request: HttpRequest, pk: int) -> HttpResponseRedirect | HttpResponseRedirect:
        obj = self.get_object(request, pk)
        payload = obj.get_payload()
        config = obj.parent.fsp.configs.get(
            key=obj.parent.extra.get("config_key"),
            delivery_mechanism__code=payload.get("delivery_mechanism"),
            fsp=obj.parent.fsp,
        )
        return redirect(reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk]))


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "external_code",
        "office",
        "remote_id",
        "fsp",
        "status",
        "active",
        "tag",
    )
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


@admin.register(Country)
class CountryAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("name", "short_name", "iso_code2", "iso_code3", "iso_num")
    search_fields = ("name", "short_name", "iso_code2", "iso_code3", "iso_num")
    ordering = ("name",)


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
class FinancialServiceProviderConfigAdmin(AdminFiltersMixin, ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "key",
        "office",
        "country",
        "label",
        "fsp",
        "delivery_mechanism",
        "required_fields",
    )
    search_fields = (
        "remote_id",
        "fsp__name",
        "country__name",
        "country__iso_code2",
        "country__iso_code3",
        "office__name",
        "office__code",
        "office__slug",
        "delivery_mechanism__name",
        "delivery_mechanism__code",
    )
    list_filter = (
        "fsp",
        "delivery_mechanism",
        ("country", AutoCompleteFilter),
        ("office", AutoCompleteFilter),
    )


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
    list_display = ("instruction", "type", "verbose_status", "action", "owner")
    autocomplete_fields = ("owner", "content_type")
    list_filter = (
        ("owner", AutoCompleteFilter),
        "type",
        "action",
    )

    def get_readonly_fields(self, request: "HttpRequest", obj: AsyncJob | None = None):
        if obj:
            return ("owner", "local_status", "type", "action", "sentry_id")
        return super().get_readonly_fields(request, obj)
