from admin_extra_buttons.decorators import choice, view
from constance import config
from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.exceptions import (
    InvalidCorridorError,
    PayloadException,
    PayloadMissingKeyError,
)
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProviderConfig,
    PaymentRecord,
)


class WesternUnionAdminMixin:
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
            if payload.get("delivery_services_code") == "800":
                try:
                    Corridor.objects.get(
                        destination_country=payload.get("destination_country"),
                        destination_currency=payload.get("destination_currency"),
                    )
                    button.choices.append(self.wu_corridor)
                except (Corridor.DoesNotExist, Corridor.MultipleObjectsReturned):
                    pass
            try:
                obj.parent.fsp.configs.get(
                    key=obj.parent.extra.get("config_key"),
                    delivery_mechanism__code=payload.get("delivery_mechanism"),
                    fsp=obj.parent.fsp,
                )
                button.choices.append(self.wu_config)
            except (
                FinancialServiceProviderConfig.DoesNotExist,
                FinancialServiceProviderConfig.MultipleObjectsReturned,
            ):
                pass
        else:
            button.visible = False
        return button

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Prepare Payload",
        permission="western_union.can_prepare_transaction",
    )
    def wu_prepare_payload(
        self, request: HttpRequest, pk: int
    ) -> TemplateResponse | HttpResponseRedirect | HttpResponseRedirect:
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
            context["request_format"] = "json"
            return TemplateResponse(request, "request.html", context)

        except (PayloadException, InvalidCorridorError, PayloadMissingKeyError) as e:
            messages.add_message(request, messages.ERROR, str(e))
            return redirect(reverse("admin:gateway_paymentrecord_change", args=[obj.pk]))

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Send Money Validation",
        permission="western_union.can_prepare_transaction",
    )
    def wu_send_money_validation(
        self, request: HttpRequest, pk: int
    ) -> TemplateResponse | HttpResponseRedirect | HttpResponseRedirect:
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
            return redirect(reverse("admin:gateway_paymentrecord_change", args=[obj.pk]))

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Send Money",
        permission="western_union.can_create_transaction",
    )
    def wu_send_money(
        self, request: HttpRequest, pk: int
    ) -> TemplateResponse | HttpResponseRedirect | HttpResponseRedirect:
        obj = PaymentRecord.objects.get(pk=pk)
        context = self.get_common_context(request, pk)
        try:
            context.update(WesternUnionClient().create_transaction(obj.get_payload()))
            return TemplateResponse(request, "request.html", context)
        except PaymentRecord.DoesNotExist:
            messages.add_message(request, messages.ERROR, "Cannot find Payment Record")
            return redirect(reverse("admin:gateway_paymentrecord_change", args=[obj.pk]))

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
            context.update(WesternUnionClient().status(obj.fsp_code, False))
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
            context.update(WesternUnionClient().status(obj.fsp_code, True))
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
            context.update(WesternUnionClient().refund(obj.fsp_code, obj.extra_data))

        return TemplateResponse(request, "request.html", context)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Corridor",
    )
    def wu_corridor(self, request: HttpRequest, pk: int) -> HttpResponseRedirect | HttpResponseRedirect:
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
    def wu_config(self, request: HttpRequest, pk: int) -> HttpResponseRedirect | HttpResponseRedirect:
        obj = self.get_object(request, pk)
        payload = obj.get_payload()
        config = obj.parent.fsp.configs.get(
            key=obj.parent.extra.get("config_key"),
            delivery_mechanism__code=payload.get("delivery_mechanism"),
            fsp=obj.parent.fsp,
        )
        return redirect(reverse("admin:gateway_financialserviceproviderconfig_change", args=[config.pk]))
