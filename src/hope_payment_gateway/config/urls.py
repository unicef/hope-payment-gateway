from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.views.generic import TemplateView

root_patterns = [
    path(r"", TemplateView.as_view(template_name="home.html"), name="home"),
    path(r"admin/", admin.site.urls),
    path(r"security/", include("unicef_security.urls", namespace="security")),
    path(r"social/", include("social_django.urls", namespace="social")),
]

api_patterns = [
    path(r"accounts/", include("django.contrib.auth.urls")),
    path(r"adminactions/", include("adminactions.urls")),
    path(
        r"wu/",
        include("hope_payment_gateway.apps.fsp.western_union.urls", namespace="wu"),
    ),
    path(
        r"moneygram/",
        include("hope_payment_gateway.apps.fsp.moneygram.urls", namespace="mg"),
    ),
    path(
        r"palpay/",
        include("hope_payment_gateway.apps.fsp.palpay.urls", namespace="pal"),
    ),
    path(r"rest/", include("hope_payment_gateway.api.docs", namespace="docs")),
    path(r"rest/", include("hope_payment_gateway.api.urls", namespace="rest")),
    path(r"sentry_debug/", lambda _: 1 / 0),
]


def ok(request) -> HttpResponse:
    return HttpResponse("OK")


urlpatterns = [
    path("api/", include(api_patterns)),
    path("health", ok),
    path("", include(root_patterns)),
]

if settings.DEBUG:  # pragma: no cover
    import debug_toolbar

    urlpatterns += [
        path(r"__debug__/", include(debug_toolbar.urls)),
    ]
