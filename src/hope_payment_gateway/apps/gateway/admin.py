from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.template.response import TemplateResponse

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminactions.export import base_export

from hope_payment_gateway.apps.fsp.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.fsp.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.gateway.actions import TemplateExportForm, export_as_template, export_as_template_impl
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("record_code", "status", "message", "success", "remote_id")
    list_filter = ("record_code", "status", "success")
    search_fields = ("transaction_id", "message")
    # readonly_fields = ("extra_data", )

    actions = [export_as_template]

    @choice(change_list=False)
    def western_union(self, button):
        button.choices = [self.send_money_validation, self.send_money, self.search_request, self.cancel]
        return button

    @view(html_attrs={"style": "background-color:#88FF88;color:black"})
    def send_money_validation(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        payload = obj.get_payload()
        context["msg"] = "First call: check if data is valid \n it returns MTCN"
        payload = create_validation_payload(payload)
        context.update(send_money_validation(payload))
        return TemplateResponse(request, "western_union.html", context)

    @view(html_attrs={"style": "background-color:#88FF88;color:black"})
    def send_money(self, request, pk) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        log = send_money(obj.get_payload())
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    @view(html_attrs={"style": "background-color:yellow;color:blue"})
    def search_request(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["msg"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
            frm = obj.extra_data.get("foreign_remote_system", None)
            context.update(search_request(frm, mtcn))
            return TemplateResponse(request, "western_union.html", context)
        messages.warning(request, "Missing MTCN")

    @view(html_attrs={"style": "background-color:#88FF88;color:black"})
    def cancel(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["obj"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
        log = cancel(obj.pk)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent__fsp")


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("unicef_id", "status", "remote_id")
    list_filter = ("status",)
    search_fields = ("unicef_id",)
    # readonly_fields = ("extra",)

    @button()
    def export(self, request, pk) -> TemplateResponse:
        obj = self.get_object(request, str(pk))
        queryset = PaymentRecord.objects.filter(parent=obj).select_related("parent__fsp")

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


class FinancialServiceProviderConfigInline(TabularInline):
    model = FinancialServiceProviderConfig
    extra = 1


@admin.register(FinancialServiceProvider)
class FinancialServiceProviderAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "vision_vendor_number",
        "remote_id",
    )
    search_fields = ("remote_id", "name", "vision_vendor_number")
    inlines = (FinancialServiceProviderConfigInline,)
