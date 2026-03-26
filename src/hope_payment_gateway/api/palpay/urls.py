from django.urls import re_path

from hope_payment_gateway.api.palpay.views import PalPayWebhook

app_name = "palpay"

urlpatterns = [
    re_path(
        "webhook_status_events/",
        view=PalPayWebhook.as_view(),
        name="palpay-status-webhook",
    ),
]
