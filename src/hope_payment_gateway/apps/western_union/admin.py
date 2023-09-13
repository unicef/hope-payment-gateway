from django.contrib import admin, messages
from django.template.response import TemplateResponse

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin

from hope_payment_gateway.apps.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.western_union.endpoints.das import (
    das_countries_currencies,
    das_delivery_option_template,
    das_delivery_services,
    das_destination_countries,
    das_destination_currencies,
    das_origination_currencies,
)
from hope_payment_gateway.apps.western_union.endpoints.request import requests_request
from hope_payment_gateway.apps.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.western_union.models import Corridor, PaymentRecordLog


@admin.register(Corridor)
class CorridorAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "description",
        "destination_country",
        "destination_currency",
        "template_code",
    )
    list_filter = (
        "destination_country",
        "destination_currency",
        "template_code",
    )
    search_fields = (
        "description",
        "template_code",
    )

    @button()
    def request(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context.update(requests_request())
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_countries_currencies(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context["msg"] = "Countries with related Currencies (Many to many)"
        context.update(das_countries_currencies())
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_origination_currencies(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context["msg"] = "Countries with related iso codes"
        context.update(das_origination_currencies())
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_destination_currencies(self, request) -> TemplateResponse:
        destination_country = request.GET.get("destination_country", "US")
        context = self.get_common_context(request)
        context["msg"] = f"currencies allowed for in {destination_country} \n " f"PARAM: destination_country"
        context.update(das_destination_currencies(destination_country))
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_destination_countries(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context["msg"] = "List of destination countries"
        context.update(das_destination_countries())
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_delivery_services(self, request) -> TemplateResponse:
        destination_country = request.GET.get("destination_country", "PH")
        destination_currency = request.GET.get("destination_currency", "PHP")
        context = self.get_common_context(request)
        context["msg"] = (
            f"Delivery Services available to transfer to destination {destination_country} {destination_currency} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency"
        )
        context.update(das_delivery_services(destination_country, destination_currency))
        return TemplateResponse(request, "western_union.html", context)

    @choice()
    def das(self, button):
        button.choices = [
            self.das_countries_currencies,
            self.das_origination_currencies,
            self.das_destination_currencies,
            self.das_destination_countries,
            self.das_delivery_services,
        ]
        return button

    @button()
    def delivery_services(self, request, pk) -> TemplateResponse:
        obj = self.model.objects.get(pk=pk)
        destination_country = obj.destination_country
        destination_currency = obj.destination_currency
        context = self.get_common_context(request)
        context["msg"] = (
            f"Delivery Services available to transfer to destination {destination_country} {destination_currency} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency"
        )
        context.update(das_delivery_services(destination_country, destination_currency))
        return TemplateResponse(request, "western_union.html", context)

    @view()
    def das_delivery_option_template(self, request) -> TemplateResponse:
        destination_country = request.GET.get("destination_country", "PH")
        destination_currency = request.GET.get("destination_currency", "PHP")
        template_code = request.GET.get("template_code", 4061)
        context = self.get_common_context(request)
        context["msg"] = (
            f"template for {destination_country} [{destination_currency}] using template {template_code} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency\n"
            f"PARAM: template_code"
        )
        context.update(das_delivery_option_template(destination_country, destination_currency, template_code))
        return TemplateResponse(request, "western_union.html", context)

    @button()
    def delivery_option_template(self, request, pk) -> TemplateResponse:
        obj = self.model.objects.get(pk=pk)
        destination_country = obj.destination_country
        destination_currency = obj.destination_currency
        template_code = obj.template_code

        context = self.get_common_context(request)
        context["msg"] = (
            f"template for {destination_country} [{destination_currency}] using template {template_code} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency\n"
            f"PARAM: template_code"
        )
        context.update(das_delivery_option_template(destination_country, destination_currency, template_code))
        return TemplateResponse(request, "western_union.html", context)


@admin.register(PaymentRecordLog)
class PaymentRecordLogAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = (
        "record_code",
        "message",
        "success",
    )
    list_filter = ("record_code", "success")
    search_fields = ("transaction_id", "message")
    readonly_fields = ("extra_data",)

    @choice(change_list=False)
    def primitives(self, button):
        button.choices = [self.send_money_validation, self.search_request]
        return button

    @view(html_attrs={"style": "background-color:#88FF88;color:black"})
    def send_money_validation(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecordLog.objects.get(pk=pk)
        context["msg"] = "First call: check if data is valid \n it returns MTCN"
        payload = create_validation_payload(obj.payload)
        context.update(send_money_validation(payload))
        return TemplateResponse(request, "western_union.html", context)

    @button()
    def send_money(self, request, pk) -> TemplateResponse:
        obj = PaymentRecordLog.objects.get(pk=pk)
        log = send_money(obj.payload)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    @view(html_attrs={"style": "background-color:yellow;color:blue"})
    def search_request(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecordLog.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["msg"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
            context.update(search_request(obj.record_code, mtcn))
            return TemplateResponse(request, "western_union.html", context)
        messages.warning(request, "Missing MTCN")

    @button()
    def cancel(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecordLog.objects.get(pk=pk)
        if mtcn := obj.extra_data.get("mtcn", None):
            context["obj"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
        log = cancel(obj.record_code, mtcn)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)
