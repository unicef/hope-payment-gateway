import base64
import logging
from contextlib import suppress
from datetime import datetime

import sentry_sdk
from constance import config
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.http import JsonResponse
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.permissions import WhitelistPermission
from hope_payment_gateway.apps.fsp.moneygram import DELIVERED, RECEIVED
from hope_payment_gateway.apps.fsp.moneygram.client import update_status
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


def verify(signature_header, unix_time_in_seconds, destination_host, body):
    data = f"{unix_time_in_seconds}.{destination_host}.{body}".encode()
    public_key_str = settings.MONEYGRAM_PUBLIC_KEY
    public_key_pem = f"-----BEGIN PUBLIC KEY-----\n{public_key_str.strip()}\n-----END PUBLIC KEY-----"
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    signature = base64.b64decode(signature_header)

    try:
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False


class MoneyGramApi(GenericAPIView):
    permission_classes = (WhitelistPermission,)


class MoneyGramWebhook(MoneyGramApi):
    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("MoneyGram: Webhook Notification")
        return super().dispatch(request, *args, **kwargs)

    def verify_signature(self, request):
        destination_host = request.headers.get("Host")

        signature_dict = {
            header.split("=", 1)[0]: header.split("=", 1)[1]
            for header in request.headers.get("Signature", "").split(",")
        }

        signature = signature_dict["s"]
        unix_time_in_seconds = signature_dict["t"]

        body = str(request.data).replace(" ", "").replace("'", '"')
        return verify(signature, unix_time_in_seconds, destination_host, body)

    def post(self, request):
        if config.MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED and not self.verify_signature(request):
            return JsonResponse({"error": "Invalid Signature header"}, status=400)
        payload = request.data
        logger.info(payload)
        record_key = payload["eventPayload"]["transactionId"]
        try:
            pr = PaymentRecord.objects.get(
                fsp_code=record_key,
                parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER,
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
                    payload["eventPayload"]["transactionStatusDate"],
                    "%Y-%m-%dT%H:%M:%S.%f",
                ).date()

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
