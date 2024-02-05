from django_fsm import TransitionNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser
from rest_framework_xml.renderers import XMLRenderer
from sentry_sdk.integrations.wsgi import get_client_ip

# from hope_payment_gateway.apps.core.permissions import get_client_ip
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
        ip_address = get_client_ip(request.META)

        record_code = payload["transaction_id"]

        mtcn = payload["money_transfer_control"]["mtcn"]
        notification_type = payload["notification_type"]

        delivered_quantity = payload["payment_details"]["origination"]["principal_amount"] / 100

        try:
            pr = PaymentRecord.objects.get(record_code=record_code)
        except PaymentRecord.DoesNotExist:
            return Response(
                {"cannot_find_transaction": f"Cannot find payment with reference {record_code}", "status": 400}
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
            return Response({"transition_not_allowed": str(e), "status": 400})

        pr.save()
        resp = nic_acknowledge(payload, ip_address)

        return Response(resp, status=resp.get("code", None))


def nic_acknowledge(payload, ip_address):
    for tag_name in ["message_code", "message_text", "reason_code", "reason_desc"]:
        payload.pop(tag_name, None)
    payload["ack_message"] = "Acknowledged"

    client = WesternUnionClient("NisNotification.wsdl")
    resp = client.response_context("NotifServiceReply", payload)
    return resp
