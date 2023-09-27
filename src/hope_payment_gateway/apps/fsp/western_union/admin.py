from django.contrib import admin
from django.template.response import TemplateResponse

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin

from hope_payment_gateway.apps.fsp.western_union.endpoints.das import (
    das_countries_currencies,
    das_delivery_option_template,
    das_delivery_services,
    das_destination_countries,
    das_destination_currencies,
    das_origination_currencies,
)
from hope_payment_gateway.apps.fsp.western_union.endpoints.request import requests_request
from hope_payment_gateway.apps.fsp.western_union.models import Corridor


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
    def western_union(self, button):
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
