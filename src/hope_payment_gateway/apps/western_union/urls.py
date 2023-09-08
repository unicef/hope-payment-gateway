from django.urls import re_path

from hope_payment_gateway.apps.western_union.endpoints.push_notification import (
    PayNotificationView,
)

app_name = "western_union"

urlpatterns = [
    re_path(
        "pay_notification/",
        view=PayNotificationView.as_view(http_method_names=["post"]),
        name="pay-notification-view",
    ),
]
