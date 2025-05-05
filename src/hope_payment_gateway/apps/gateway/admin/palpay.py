import logging

from admin_extra_buttons.decorators import choice, view
from constance import config
from django.contrib import messages
from django.http import HttpRequest
from django.template.response import TemplateResponse

from hope_payment_gateway.apps.fsp.palpay.client import PalPayClient
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


class PalPayAdminMixin:
    def handle_pal_response(self, request: HttpRequest, pk: int, method: str, title: str) -> TemplateResponse:
        obj = PaymentRecord.objects.get(pk=pk)
        try:
            client_call = getattr(PalPayClient(), method)
            payload, resp = client_call(obj.fsp_code, obj.get_payload())
            context = self.get_common_context(request, pk)
            if resp:
                context["code"] = resp.status_code
                context["title"] = title
                context["request_format"] = "json"
                context["response_format"] = "json"
                context["content_request"] = payload
                context["content_response"] = resp.data
            else:
                messages.add_message(request, messages.ERROR, "Connection Error")
            return TemplateResponse(request, "request.html", context)
        except KeyError as e:
            logger.error(e)
            self.message_user(request, str(e), messages.ERROR)

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Create Transaction",
        permission="palpay.can_create_transaction",
    )
    def pal_create_transaction(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_pal_response(request, pk, "create_transaction", "Create Transaction")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Check Status",
        permission="palpay.can_check_status",
    )
    def pal_status(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_pal_response(request, pk, "status", "Check Status")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Update Status",
        permission="palpay.can_update_status",
    )
    def pal_status_update(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_pal_response(request, pk, "status_update", "Update Status")

    @view(
        html_attrs={"style": "background-color:#88FF88;color:black"},
        label="Cancel",
        permission="palpay.can_cancel_transaction",
    )
    def pal_refund(self, request: HttpRequest, pk: int) -> TemplateResponse:
        return self.handle_pal_response(request, pk, "status_update", "Cancel")

    @choice(change_list=False, label="PalPay")
    def palpay(self, button):
        obj: PaymentRecord = button.original
        if obj.parent.fsp.vendor_number == config.PALPAY_VENDOR_NUMBER:
            button.choices = [
                self.pal_create_transaction,
                self.pal_status,
                self.pal_status_update,
                self.pal_refund,
            ]
        else:
            button.visible = False
        return button
