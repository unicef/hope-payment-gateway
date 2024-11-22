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

    def verify(self):
        # todo
        # const publicKey = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Dm7LFleQyaXakYdNOvCv2Irm2ufOcncek0Q4J+MtzmEYvdlfhx5Sm206s2Z5l0/+6YyA3tFljRNCFar3lm96o/S6IFNo0xOsCy+Il7EzQNl4S7kojqnOGfgMgUBC/qxf0S7zkh7y0St8G3OpcjYg7Ff7PAFXmcgjk22F1lUeOqy+zyP2dRJ+NEKZrcHJhbFheB0dPH++e+1foHSfhz+I+Pt9DDaESJasJptZGo0Ww3U+KkPmrDriOLbvpdE4r7MKzeQfGa7SMx4VzhtWFa98/6V6MO29ZjkegejHBZsCekA/1NU0gAQhQnxuYsgdCn/9LogrWqUS8Tl44K2yPYCsQIDAQAB";
        # function verify(signatureHeader, unixTimeInSeconds, destinationHost, body){
        #
        #     // Using Hashing Algorithm
        #     const algorithm = "RSA-SHA256";
        #
        #     // Converting string to buffer
        #     const data = Buffer.from(unixTimeInSeconds+"."+destinationHost+"."+body);
        #
        #     const pub = "-----BEGIN PUBLIC KEY-----\n" + publicKey + "\n-----END PUBLIC KEY-----";
        #
        #     // Verifying signature using crypto.verify() function
        #     const isVerified = crypto.verify(algorithm, data, pub, Buffer.from(signatureHeader, "base64"));
        #
        #     // Printing the result
        #     console.log('Is signature verified: '+isVerified);
        #
        #     return isVerified;
        # }
        return bool(settings.MONEYGRAM_PUBLIC_KEY)

        # const signatureHeader = "wGIPt8Wt16Vl9yMGEBO7ByZA8zkJzuUjaE/2G5NDez8SEGDnX5VdxoSqdTN8N6/LaX2jV/9o25fWppJoxBBK6g/SHKFAo/Ib8uOnNYWeyjdrhZ4RVBCmB+IcdKuSXZHWFwtCLZM0R6PitE4HkXJrooe5KY93VzR8migLd7bw4ANAFwhYLBn6JmfnKO78A1hqpsUsq1T28Aph+6mYPx2q4SrfpkKK/YAoZrCpZMR/nzZMYevJhupy4i7B2L5axv94gm6YKZkaTAjCJWtXp2Kkv+UQ4Dpo7I+DkxWObg8dCy1JfzLlh57XswSdyiombhizHI89MgW4j1IWHZ4EZWxc6Q==";
        # const unixTimeInSeconds = 1679925945;
        # const destinationHost = "sandbox.com";
        # const body = "{\"eventId\":\"740708201679925945014500444747\",\"eventDate\":\"2023-03-27T14:05:44.884026\",\"subscriptionId\":\"15efa8b3-bb09-4fe9-a295-55fc323cf3ee\",\"subscriptionType\":\"TRANSACTION_STATUS_EVENT\",\"eventPayload\":{\"transactionId\":\"3009143868\",\"agentPartnerId\":\"74097706\",\"referenceNumber\":\"40196296\",\"transactionSendDate\":\"2023-03-27T14:05:41.007\",\"transactionStatusDate\":\"2023-03-27T14:05:41.007\",\"transactionStatus\":\"SENT\",\"transactionSubStatus\":[]}}";
        # verify(signatureHeader, unixTimeInSeconds, destinationHost, body);

    def post(self, request):
        payload = request.data
        self.verify()
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
