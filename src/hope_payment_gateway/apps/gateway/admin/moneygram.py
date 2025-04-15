import logging

from admin_extra_buttons.decorators import choice, view
from constance import config
from django.contrib import messages
from django.http import HttpRequest
from django.template.response import TemplateResponse
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.fsp.moneygram.client import (
    InvalidTokenError,
    MoneyGramClient,
)
from hope_payment_gateway.apps.gateway.models import PaymentRecord, FinancialServiceProviderConfig

logger = logging.getLogger(__name__)


class MoneyGramAdminMixin:
    def handle_mg_response(self, request: HttpRequest, pk: int, method: str, title: str) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            try:
                payload, resp = getattr(MoneyGramClient(), method)(obj.get_payload())
                context = self.get_common_context(request, pk)
                if resp:
                    if resp.status_code < 300:
                        context["title"] = title
                        context["request_format"] = "json"
                        context["response_format"] = "json"
                        context["content_request"] = payload
                        context["content_response"] = resp.data
                        return TemplateResponse(request, "request.html", context)

                    loglevel, msgs = self.handle_error(resp)

                    for msg in msgs:
                        messages.add_message(request, loglevel, msg)
                else:
                    messages.add_message(request, messages.ERROR, "Connection Error")
                return TemplateResponse(request, "request.html", context)

            except KeyError as e:
                self.message_user(request, f"Keyerror: {str(e)}", messages.ERROR)
            except TransitionNotAllowed as e:
                self.message_user(request, str(e), messages.ERROR)
        except InvalidTokenError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Create Transaction",
        permission="moneygram.can_create_transaction",
    )
    def mg_create_transaction(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "create_transaction", "Create Transaction")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Quote",
        permissions="moneygram.can_quote_transaction",
    )
    def mg_quote_transaction(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "quote", "Quote")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Status",
        permission="moneygram.can_check_status",
    )
    def mg_status(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "status", "Status")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Status Update",
        permission="moneygram.can_update_status",
    )
    def mg_status_update(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "status_update", "Status Upload")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Required Fields",
        permission="moneygram.can_quote_transaction",
    )
    def mg_get_required_fields(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "get_required_fields", "Required Fields")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Service Options",
        permission="moneygram.can_quote_transaction",
    )
    def mg_get_service_options(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "get_service_options", "Service Options")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Refund",
        permission="moneygram.can_cancel_transaction",
    )
    def mg_refund(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_mg_response(request, pk, "refund", "Refund")

    @choice(change_list=False, label="MoneyGram")
    def moneygram(self, button):
        obj: PaymentRecord = button.original
        if obj.parent.fsp.vendor_number == config.MONEYGRAM_VENDOR_NUMBER:
            button.choices = [
                self.mg_create_transaction,
                self.mg_quote_transaction,
                self.mg_status,
                self.mg_status_update,
                self.mg_get_service_options,
                self.mg_get_required_fields,
                self.mg_refund,
            ]
            payload = obj.get_payload()
            try:
                obj.parent.fsp.configs.get(
                    key=obj.parent.extra.get("config_key"),
                    delivery_mechanism__code=payload.get("delivery_mechanism"),
                    fsp=obj.parent.fsp,
                )
                button.choices.append(self.configuration)
            except (
                FinancialServiceProviderConfig.DoesNotExist,
                FinancialServiceProviderConfig.MultipleObjectsReturned,
            ):
                pass
        else:
            button.visible = False
        return button
