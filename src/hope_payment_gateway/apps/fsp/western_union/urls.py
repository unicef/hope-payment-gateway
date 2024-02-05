from django.urls import re_path

from hope_payment_gateway.apps.fsp.western_union.endpoints.nis import NisNotificationView

app_name = "western_union"

urlpatterns = [
    re_path(
        "nis_complete/",
        view=NisNotificationView.as_view(),
        name="nis-notification-view",
    ),
]
