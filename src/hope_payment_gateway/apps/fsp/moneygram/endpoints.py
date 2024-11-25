from django.conf import settings

import sentry_sdk
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.permissions import WhitelistPermission
from hope_payment_gateway.apps.fsp.moneygram.client import update_status
from hope_payment_gateway.apps.gateway.models import PaymentRecord


class MoneyGramApi(APIView):
    permission_classes = (WhitelistPermission,)


class MoneyGramWebhook(MoneyGramApi):

    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("MoneyGram: Webhook Notification")
        return super().dispatch(request, *args, **kwargs)

    def verify(self, request):
        return settings.MONEYGRAM_PUBLIC_KEY

    def post(self, request):
        payload = request.data
        # self.verify()
        try:
            record_key = payload["eventPayload"]["transactionId"]
        except KeyError:
            return Response(
                {"cannot_retrieve ID": "missing eventPayload > transactionId"},
                status=HTTP_400_BAD_REQUEST,
            )
        try:
            pr = PaymentRecord.objects.get(fsp_code=record_key)
        except PaymentRecord.DoesNotExist:
            return Response(
                {"cannot_find_transaction": f"Cannot find payment with provided reference {record_key}"},
                status=HTTP_400_BAD_REQUEST,
            )
        try:
            self.update_record(pr, payload)
        except TransitionNotAllowed:
            return Response({"error": "transition_not_allowed"}, status=HTTP_400_BAD_REQUEST)

        return Response(payload)

    @staticmethod
    def update_record(pr, payload):
        notification_type = payload["eventPayload"]["transactionStatus"]
        update_status(pr, notification_type)

        pr.extra_data.update(
            {
                "eventId": payload["eventId"],
                "eventDate": payload["eventDate"],
                "subscriptionType": payload["subscriptionType"],
                "transactionSubStatus": [
                    {"status": substatus["subStatus"], "message": substatus["message"]}
                    for substatus in payload["eventPayload"]["transactionSubStatus"]
                ],
            }
        )
        pr.save()
