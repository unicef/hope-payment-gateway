from django.urls import re_path

from hope_payment_gateway.api.western_union.views.webhook import (
    NisNotificationJSONView,
    NisNotificationXMLView,
)

app_name = "western_union"

urlpatterns = [
    re_path(
        "nis_complete/",
        view=NisNotificationXMLView.as_view(),
        name="nis-notification-xml-view",
    ),
    re_path(
        "nis_json_complete/",
        view=NisNotificationJSONView.as_view(),
        name="nis-notification-json-view",
    ),
]
