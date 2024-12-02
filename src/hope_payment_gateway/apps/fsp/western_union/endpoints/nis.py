from django.http import HttpResponse

import sentry_sdk
from constance import config
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser
from rest_framework_xml.renderers import XMLRenderer
from viewflow.fsm import TransitionNotAllowed
from zeep.exceptions import ValidationError

from hope_payment_gateway.apps.core.permissions import WhitelistPermission
from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.exceptions import InvalidRequest
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import PaymentRecord

SUCCESS = "BIS003"
CANCEL = "BIS005"
REFUND = "BIS006"
PURGED = "BIS016"
REJECT_APN = "BIS011"
SUCCESS_APN = "BIS012"


class WesternUnionApi(APIView):
    permission_classes = (WhitelistPermission,)
    serializer_class = None


class XMLViewMixin:
    parser_classes = (XMLParser,)
    renderer_classes = (XMLRenderer,)


class NisNotificationView(WesternUnionApi):
    content_type = None

    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("Western Union: NIS Notification")
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def get_payload(request):
        return request.data

    @staticmethod
    def prepare_response(payload):  # TODO
        return payload

    def get(self, request):
        try:
            payload = self.get_payload(request)
        except InvalidRequest as e:
            return Response(
                {"invalid_request": str(e)},
                status=HTTP_400_BAD_REQUEST,
            )
        return Response(payload)

    def post(self, request):
        try:
            payload = self.get_payload(request)
        except InvalidRequest as e:
            return Response(
                {"invalid_request": str(e)},
                status=HTTP_400_BAD_REQUEST,
            )
        fsp_code = payload["transaction_id"]
        mtcn = payload["money_transfer_control"]["mtcn"]
        notification_type = payload["notification_type"]
        payout_amount = payload["payment_details"]["destination"]["expected_payout_amount"]

        try:
            for tag_name in ["message_code", "message_text", "reason_code", "reason_desc"]:
                payload.pop(tag_name, None)
            payload["ack_message"] = "Acknowledged"
            resp = self.prepare_response(payload)
        except ValidationError as exp:
            return Response({"validation_error": str(exp)}, status=HTTP_400_BAD_REQUEST)

        try:
            pr = PaymentRecord.objects.get(
                fsp_code=fsp_code, parent__fsp__vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
            )
            flow = PaymentRecordFlow(pr)
        except PaymentRecord.DoesNotExist:
            return Response(
                {"cannot_find_transaction": f"Cannot find payment with reference {fsp_code}"},
                status=HTTP_400_BAD_REQUEST,
            )

        pr.success = False
        try:
            if notification_type in [SUCCESS, SUCCESS_APN]:
                flow.confirm()
                pr.success = True
                pr.payout_amount = payout_amount / 100
                pr.extra_data.update(
                    {
                        "mtcn": mtcn,
                        "message_code": notification_type,
                    }
                )
            elif notification_type in [CANCEL, REJECT_APN]:
                flow.cancel()
            elif notification_type == PURGED:
                flow.purge()
            elif notification_type == REFUND:
                flow.refund()
            else:
                flow.fail()
        except TransitionNotAllowed:
            return Response({"error": "transition_not_allowed"}, status=HTTP_400_BAD_REQUEST)

        pr.save()

        return HttpResponse(resp, content_type="application/xml")


class NisNotificationJSONView(NisNotificationView):
    pass


class NisNotificationXMLView(XMLViewMixin, NisNotificationView):

    @staticmethod
    def get_payload(request):
        header = "{http://schemas.xmlsoap.org/soap/envelope/}Body"
        secondary_header = "{http://www.westernunion.com/schema/xrsi}nis-notification-request"

        try:
            return request.data[header][secondary_header]
        except KeyError:
            if header in request.data:
                key = secondary_header
                keys = ", ".join(request.data[header].keys())
            else:
                key = header
                keys = ", ".join(request.data.keys())
            raise InvalidRequest(f"header {key} not in {keys}")

    @staticmethod
    def prepare_response(payload):
        client = WesternUnionClient("NisNotification.wsdl")
        _, data = client.prepare("NotifServiceReply", payload)
        return data
