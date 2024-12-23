import base64
import binascii
import logging

from django.conf import settings

import cryptography.exceptions
import sentry_sdk
from constance import config
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from viewflow.fsm import TransitionNotAllowed

from hope_payment_gateway.apps.core.permissions import WhitelistPermission
from hope_payment_gateway.apps.fsp.moneygram.client import update_status
from hope_payment_gateway.apps.gateway.models import PaymentRecord

logger = logging.getLogger(__name__)


class MoneyGramApi(APIView):
    permission_classes = (WhitelistPermission,)


class MoneyGramWebhook(MoneyGramApi):
    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("MoneyGram: Webhook Notification")
        return super().dispatch(request, *args, **kwargs)

    def verify(self, request):
        header_dict = {
            header.split("=", 1)[0]: header.split("=", 1)[1]
            for header in request.headers.get("Signature", "").split(",")
        }

        destination_host = "f-p-sandbox.snssdk.com"
        public_key = f"""-----BEGIN PUBLIC KEY-----
        {settings.MONEYGRAM_PUBLIC_KEY}
        -----END PUBLIC KEY-----"""
        pub_key = serialization.load_pem_public_key(public_key.encode("utf-8"), backend=default_backend())

        unix_time_in_seconds = header_dict.get("t")

        signature_header = header_dict.get("s", "")
        signature = base64.b64decode(signature_header)

        body = request.body
        data = f"{unix_time_in_seconds}.{destination_host}.{body}".encode()

        pub_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())

    def post(self, request):
        try:
            self.verify(request)
        except (IndexError, cryptography.exceptions.InvalidSignature, binascii.Error):
            if config.MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED:
                return Response(
                    {"cannot_decrypt_signature": "Signature is invalid or expired"},
                    status=HTTP_400_BAD_REQUEST,
                )
            else:
                logger.warning("Moneygram signature verification invalid")
        payload = request.data
        try:
            record_key = payload["eventPayload"]["transactionId"]
        except KeyError:
            return Response(
                {"cannot_retrieve ID": "missing eventPayload > transactionId"},
                status=HTTP_400_BAD_REQUEST,
            )
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
