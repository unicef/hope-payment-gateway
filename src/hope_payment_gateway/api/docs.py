from django.urls import re_path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

app_name = "docs"

urlpatterns = [
    re_path("^$", SpectacularAPIView.as_view(), name="schema"),
    re_path(
        "^swagger-ui/$",
        SpectacularSwaggerView.as_view(url_name="docs:schema"),
        name="swagger-ui",
    ),
    re_path("^redoc/$", SpectacularRedocView.as_view(url_name="docs:schema"), name="redoc"),
]
