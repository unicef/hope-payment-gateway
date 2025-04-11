import logging

import sentry_sdk
from rest_framework.generics import GenericAPIView

from hope_payment_gateway.apps.core.permissions import WhitelistPermission

logger = logging.getLogger(__name__)


class PalPayApi(GenericAPIView):
    permission_classes = (WhitelistPermission,)


class PalPayWebhook(PalPayApi):
    def dispatch(self, request, *args, **kwargs):
        sentry_sdk.capture_message("PalPay: Webhook Notification")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        pass

    @staticmethod
    def update_record(pr, payload):
        pass
