from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.models import PaymentRecord

SUCCESS = "DVQRFB51"
PURGED = "PURGED"
REFUND = "REFUND"


class PayNotificationView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = [XMLParser]

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
        msg = payload["message_text"]
        msg_code = payload["message_code"]

        delivered_quantity = payload["payment_details"]["origination"]["principal_amount"] / 100

        pr, updated = PaymentRecord.objects.update_or_create(
            record_code=record_code,
            defaults={
                "message": msg,
                "extra_data": {
                    "mtcn": mtcn,
                    "message_code": msg_code,
                    "delivered_quantity": delivered_quantity,
                },
            },
        )

        pr.message = msg
        pr.success = False

        if msg_code == SUCCESS:
            pr.confirm()
            pr.success = True
        elif msg_code == PURGED:
            pr.purge()
        elif msg_code == REFUND:
            pr.refund()
        else:
            pr.error()

        pr.save()
        resp = nic_acknowledge(payload)

        return Response(resp)


def nic_acknowledge(payload):
    payload.pop("notification_type")
    payload.pop("message_code")
    payload.pop("message_text")
    payload["ack_message"] = "SUCCESS"

    client = WesternUnionClient("NisNotification.wsdl")
    return client.response_context("NotifServiceReply", payload)
