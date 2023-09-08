from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_xml.parsers import XMLParser


class PayNotificationView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = [XMLParser]

    def post(self, request):
        """Return All Static values used for drop-down in the frontend"""
        payload = request.data["{http://schemas.xmlsoap.org/soap/envelope/}Body"][
            "{http://www.westernunion.com/schema/xrsi}nis-notification-request"
        ]
        return Response(payload)
