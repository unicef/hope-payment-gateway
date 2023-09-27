from django.urls import re_path

from hope_payment_gateway.apps.fsp.western_union.endpoints.nis import NisNotificationView, PayNotificationView

app_name = "western_union"

urlpatterns = [
    re_path(
        "pay_notification/",
        view=PayNotificationView.as_view(http_method_names=["post"]),
        name="pay-notification-view",
    ),
    re_path(
        "nis_complete/",
        view=NisNotificationView.as_view(http_method_names=["post"]),
        name="nis-notification-view",
    ),
]
