import csv
from typing import List

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.utils import timezone

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin

from hope_payment_gateway.apps.fsp.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.fsp.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord
from hope_payment_gateway.apps.gateway.templatetags.payment import get_value


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("record_code", "status", "message", "success", "uuid")
    list_filter = ("record_code", "status", "success")
    search_fields = ("transaction_id", "message")
    # readonly_fields = ("extra_data", "uuid")

    @choice(change_list=False)
    def primitives(self, button):
        button.choices = [self.send_money_validation, self.search_request]
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

    @button()
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
            context.update(search_request(obj.get_payload(), mtcn))
            return TemplateResponse(request, "western_union.html", context)
        messages.warning(request, "Missing MTCN")

    @button()
    def cancel(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["obj"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
        log = cancel(obj.uuid, mtcn)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)


class ExportForm(forms.Form):
    record_fields = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="one line for each field we want to export",
    )

    # def __init__(self, *args: Any, **kwargs: Any) -> None:
    #     if request := kwargs.pop("request", None):
    #         if is_root(request):
    #             self.base_fields["status"].choices = self.STATUSES_CHOICES + self.STATUSES_ROOT_CHOICES
    #     super().__init__(*args, **kwargs)

    def clean_record_fields(self) -> List:
        return self.cleaned_data["record_fields"].split("\r\n")


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ("unicef_id", "status", "uuid")
    list_filter = ("status",)
    search_fields = ("unicef_id",)
    # readonly_fields = ("uuid", "payload")

    @button()
    def export(self, request, pk) -> TemplateResponse:
        ctx = self.get_common_context(request, title="Export Payment Instruction")
        if request.method == "POST":
            obj = self.get_object(request, str(pk))
            qs = PaymentRecord.objects.filter(parent=obj).select_related("parent__fsp")
            form = ExportForm(request.POST)
            if form.is_valid():
                if fields := form.cleaned_data.get("record_fields", None):
                    ctx["fields"] = fields
            if "preview" in request.POST:
                ctx["qs"] = qs[:2]
            elif "export" in request.POST:
                response = HttpResponse(content_type="text/csv")
                filename = "{}_export_{}.csv".format(obj.unicef_id, timezone.now().date())
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                headers = ctx["fields"]
                writer = csv.writer(response)
                writer.writerow(headers)
                for item in qs:
                    writer.writerow([get_value(item, field) for field in headers])
                return response
        else:
            form = ExportForm()

        ctx["form"] = form
        return render(request, "payment_instruction/export.html", ctx)


@admin.register(FinancialServiceProvider)
class FinancialServiceProviderAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "vision_vendor_number",
    )
    search_fields = ("name", "vision_vendor_number")
