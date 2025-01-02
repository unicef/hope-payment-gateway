from django.contrib import admin
from django.db.models import JSONField
from django.http import HttpRequest
from django.template.response import TemplateResponse

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin
from constance import config
from jsoneditor.forms import JSONEditor

from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.api.request import requests_request
from hope_payment_gateway.apps.fsp.western_union.models import (
    Corridor,
    ServiceProviderCode,
)


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
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }

    @button()
    def request(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context.update(requests_request())
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_countries_currencies(self, request) -> TemplateResponse:
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        context = self.get_common_context(request)
        context["msg"] = (
            "Countries with related Currencies (Many to many) \n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(WesternUnionClient().das_countries_currencies(identifier, counter_id))
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_origination_currencies(self, request) -> TemplateResponse:
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        context = self.get_common_context(request)
        context["msg"] = (
            "Countries with related iso codes \n "
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(WesternUnionClient().das_origination_currencies(identifier, counter_id))
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_destination_currencies(self, request) -> TemplateResponse:
        destination_country = request.GET.get("destination_country", "US")
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)

        context = self.get_common_context(request)
        context["msg"] = (
            f"currencies allowed for in {destination_country} \n "
            f"PARAM: destination_country -> {destination_country}\n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(WesternUnionClient().das_destination_currencies(destination_country, identifier, counter_id))
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_destination_countries(self, request) -> TemplateResponse:
        context = self.get_common_context(request)
        context["msg"] = "List of destination countries"

        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        context["msg"] = (
            f"List of destination countries \n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(WesternUnionClient().das_destination_countries(identifier, counter_id))
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_delivery_services(self, request) -> TemplateResponse:
        destination_country = request.GET.get("destination_country", "PH")
        destination_currency = request.GET.get("destination_currency", "PHP")
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)

        context = self.get_common_context(request)
        context["msg"] = (
            f"Delivery Services available to transfer to destination {destination_country} {destination_currency} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency \n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(
            WesternUnionClient().das_delivery_services(
                destination_country, destination_currency, identifier, counter_id
            )
        )
        return TemplateResponse(request, "request.html", context)

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
    def delivery_services(self, request: HttpRequest, pk: int) -> TemplateResponse:
        obj = self.model.objects.get(pk=pk)
        destination_country = obj.destination_country
        destination_currency = obj.destination_currency
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        context = self.get_common_context(request)
        context["msg"] = (
            f"Delivery Services available to transfer to destination {destination_country} {destination_currency} \n "
            f"PARAM: destination_country \n"
            f"PARAM: destination_currency \n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(
            WesternUnionClient().das_delivery_services(
                destination_country, destination_currency, identifier, counter_id
            )
        )
        return TemplateResponse(request, "request.html", context)

    @view()
    def das_delivery_option_template(self, request) -> TemplateResponse:  # noqa
        destination_country = request.GET.get("destination_country", "PH")
        destination_currency = request.GET.get("destination_currency", "PHP")
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        template_code = request.GET.get("template_code", 4061)
        context = self.get_common_context(request)
        context["msg"] = (
            f"template for {destination_country} [{destination_currency}] using template {template_code} \n "
            f"PARAM: destination_country -> {destination_country} \n"
            f"PARAM: destination_currency -> {destination_currency}\n"
            f"PARAM: template_code -> {template_code} \n"
            f"PARAM: identifier -> {identifier} \n"
            f"PARAM: counter_id -> {counter_id}"
        )
        context.update(
            WesternUnionClient().das_delivery_option_template(
                destination_country,
                destination_currency,
                identifier,
                counter_id,
                template_code,
            )
        )
        return TemplateResponse(request, "request.html", context)

    @button()
    def delivery_option_template(self, request: HttpRequest, pk: int) -> TemplateResponse:
        identifier = request.GET.get("identifier", config.WESTERN_UNION_DAS_IDENTIFIER)
        counter_id = request.GET.get("counter_id", config.WESTERN_UNION_DAS_COUNTER)
        obj = self.model.objects.get(pk=pk)
        destination_country = obj.destination_country
        destination_currency = obj.destination_currency
        template_code = obj.template_code

        context = self.get_common_context(request)
        context["msg"] = (
            f"template for {destination_country} [{destination_currency}] using template {template_code} \n "
            f"PARAM: destination_country -> {destination_country}\n"
            f"PARAM: destination_currency -> {destination_currency}\n"
            f"PARAM: template_code -> {template_code}"
        )
        client = WesternUnionClient()
        context.update(
            client.das_delivery_option_template(
                destination_country,
                destination_currency,
                identifier,
                counter_id,
                template_code,
            )
        )
        return TemplateResponse(request, "request.html", context)


@admin.register(ServiceProviderCode)
class ServiceProviderCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "country", "currency")
    search_fields = ("code", "description", "country", "currency")
    list_filter = ("country", "currency")
