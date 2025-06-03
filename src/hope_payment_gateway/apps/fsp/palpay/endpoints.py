import logging
from contextlib import suppress
from datetime import datetime

import sentry_sdk
from constance import config
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.permissions import WhitelistPermission
from hope_payment_gateway.apps.fsp.palpay import RECEIVED, DELIVERED
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


class PalPayApi(GenericAPIView):
    permission_classes = (WhitelistPermission,)


class PalPayWebhook(PalPayApi):
    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("PalPay: Webhook Notification")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        payload = request.data
        logger.info(payload)
        record_key = payload["eventPayload"]["transactionId"]
        try:
            pr = PaymentRecord.objects.get(
                fsp_code=record_key,
                parent__fsp__vendor_number=config.PALPAY_VENDOR_NUMBER,
            )
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

        if notification_type in [RECEIVED, DELIVERED]:
            with suppress(KeyError, ValueError):
                pr.payout_date = datetime.strptime(
                    payload["eventPayload"]["transactionStatusDate"], "%Y-%m-%dT%H:%M:%S.%f"
                ).date()

        # update_status(pr, notification_type)

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
