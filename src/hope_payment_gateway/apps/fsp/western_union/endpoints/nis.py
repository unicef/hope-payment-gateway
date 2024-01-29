from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecord

SUCCESS = "BIS003"
REFUND = "BIS006"
CANCEL = "BIS005"
REJECT = "DVQRFB62"


class PayNotificationView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = [XMLParser]
    serializer_class = None

    def post(self, request):
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]
        return Response(payload)


class NisNotificationView(PayNotificationView):
    def post(self, request):
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]
        mtcn = payload["money_transfer_control"]["mtcn"]
        record_code = payload["transaction_id"]
        notification_type = payload["notification_type"]

        delivered_quantity = payload["payment_details"]["origination"]["principal_amount"] / 100

        pr = PaymentRecord.objects.get(record_code=record_code)
        pr.success = False

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

        pr.save()
        resp = nic_acknowledge(payload)

        return Response(resp, status=resp.get("code", None))


def nic_acknowledge(payload):
    payload.pop("message_code")
    payload.pop("message_text")
    # payload["ack_message"] = "SUCCESS"

    client = WesternUnionClient("NisNotification.wsdl")
    return client.response_context("NotifService", payload)
