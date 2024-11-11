from django.urls import re_path

from hope_payment_gateway.apps.fsp.moneygram.endpoints import MoneyGramWebhook

app_name = "moneygram"

urlpatterns = [
    re_path(
        "webhook_status_events/",
        view=MoneyGramWebhook.as_view(),
        name="mg-status-webhook",
    ),
]
