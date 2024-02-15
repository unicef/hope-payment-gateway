from django.http import HttpResponse

from django_fsm import TransitionNotAllowed
from lxml import etree
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser
from rest_framework_xml.renderers import XMLRenderer
from zeep.exceptions import ValidationError

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecord

SUCCESS = "BIS003"
REFUND = "BIS006"
CANCEL = "BIS005"
REJECT = "DVQRFB62"


class WesternUnionApi(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (XMLParser,)
    serializer_class = None
    renderer_classes = (XMLRenderer,)


class NisNotificationView(WesternUnionApi):
    def get(self, request):
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]

        return Response(payload)

    def post(self, request):
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]
        fsp_code = payload["transaction_id"]

        mtcn = payload["money_transfer_control"]["mtcn"]
        notification_type = payload["notification_type"]

        delivered_quantity = payload["payment_details"]["origination"]["principal_amount"]

        try:
            pr = PaymentRecord.objects.get(fsp_code=fsp_code)
        except PaymentRecord.DoesNotExist:
            return Response(
                {"cannot_find_transaction": f"Cannot find payment with reference {fsp_code}"},
                status=HTTP_400_BAD_REQUEST,
            )

        pr.success = False
        try:
            if notification_type == SUCCESS:
                pr.confirm()
                pr.success = True
                pr.extra_data.update(
                    {
                        "mtcn": mtcn,
                        "message_code": notification_type,
                        "delivered_quantity": delivered_quantity,
                    }
                )
            elif notification_type == CANCEL:
                pr.cancel()
            elif notification_type == REJECT:
                pr.purge()
            elif notification_type == REFUND:
                pr.refund()
            else:
                pr.error()
        except TransitionNotAllowed as e:
            return Response({"transition_not_allowed": str(e)}, status=HTTP_400_BAD_REQUEST)

        pr.save()

        try:
            resp = nic_acknowledge(payload)
        except ValidationError as exp:
            return Response({"validation_error": str(exp)}, status=HTTP_400_BAD_REQUEST)
        return HttpResponse(resp, content_type="application/xml")


def nic_acknowledge(payload):
    for tag_name in ["message_code", "message_text", "reason_code", "reason_desc"]:
        payload.pop(tag_name, None)
    payload["ack_message"] = "Acknowledged"

    client = WesternUnionClient("NisNotification.wsdl")
    node = client.prepare("NotifServiceReply", payload)
    data = etree.tostring(node, pretty_print=True, with_tail=True).decode()
    return data
