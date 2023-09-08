from django.shortcuts import redirect

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser

from hope_payment_gateway.apps.hope.models import PaymentRecord
from hope_payment_gateway.apps.western_union.endpoints.nis_acknovedge import nic_acknowledge
from hope_payment_gateway.apps.western_union.models import Log


class NisNotificationView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = [XMLParser]

    def post(self, request):
        """Return All Static values used for drop-down in the frontend"""
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]
        mtcn = payload["money_transfer_control"]["mtcn"]
        transaction_id = payload["transaction_id"]
        msg = payload["message_text"]
        msg_code = payload["message_code"]

        delivered_quantity = payload["payment_details"]["origination"]["principal_amount"] / 100
        try:
            pr = PaymentRecord.objects.get(transaction_reference_id=transaction_id)

        except PaymentRecord.DoesNotExist:
            Log.objects.create(
                transaction_id=transaction_id,
                message=msg,
                success=False,
                extra_data={
                    "mtcn": mtcn,
                    "message_code": msg_code,
                },
            )
            return redirect("admin:hope_paymentrecord_changelist")

        if msg == "Receiver Paid Notification":
            pr.status = (
                PaymentRecord.STATUS_DISTRIBUTION_SUCCESS
                if PaymentRecord.entitlement_quantity == delivered_quantity
                else PaymentRecord.STATUS_DISTRIBUTION_PARTIAL
            )
            pr.delivered_quantity = delivered_quantity
        else:
            pr.status = PaymentRecord.STATUS_ERROR
        pr.save()
        resp = nic_acknowledge(payload)

        return Response(resp)
