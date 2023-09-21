import datetime
import os
from pathlib import Path
from typing import Dict

import environ
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

SETTINGS_DIR = Path(__file__).parent
PACKAGE_DIR = SETTINGS_DIR.parent
DEVELOPMENT_DIR = PACKAGE_DIR.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env()

DEBUG = env.bool("DEBUG")

DATABASES = {
    "default": env.db(default="psql://postgres:pass@db:5432/postgres"),
}

DATABASE_ROUTERS = ("hope_payment_gateway.apps.core.dbrouters.DbRouter",)
DATABASE_APPS_MAPPING: Dict[str, str] = {
    "hope": "hope",
}

INSTALLED_APPS = (
    "hope_payment_gateway.web",
    "hope_payment_gateway.apps.core.apps.AppConfig",
    "hope_payment_gateway.apps.western_union.apps.AppConfig",
    "django.contrib.contenttypes",
    "advanced_filters",
    "unicef_security",
    "django.contrib.auth",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django.contrib.admin",
    "django_extensions",
    "django_filters",
    "corsheaders",
    "django_fsm",
    "social_django",
    "admin_extra_buttons",
    "adminactions",
    "adminfilters",
    "adminfilters.depot",
    "smart_admin.apps.SmartTemplateConfig",
    "import_export",
    "constance",
    "rest_framework",
)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "unicef_security.middleware.UNICEFSocialAuthExceptionMiddleware",
)

AUTHENTICATION_BACKENDS = (
    "unicef_security.backends.UNICEFAzureADB2COAuth2",
    "django.contrib.auth.backends.ModelBackend",
)


# path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
MEDIA_ROOT = env("MEDIA_ROOT", default="/tmp/media/")
STATIC_ROOT = env("STATIC_ROOT", default=os.path.join(BASE_DIR, "static"))
MEDIA_URL = "/dm-media/"
STATIC_URL = env("STATIC_URL", default="/static/")
STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = (
    env("ALLOWED_HOST", default="localhost"),
    "0.0.0.0",
)

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_URL = "/accounts/logout"
LOGOUT_REDIRECT_URL = "/"

# TIME_ZONE = env('TIME_ZONE')

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"
ugettext = lambda s: s  # noqa
LANGUAGES = (
    ("es", ugettext("Spanish")),
    ("fr", ugettext("French")),
    ("en", ugettext("English")),
    ("ar", ugettext("Arabic")),
)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
SITE_ID = 1
INTERNAL_IPS = ["127.0.0.1", "localhost"]

USE_I18N = True
USE_TZ = True


# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.redis.RedisCache",
#         "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
#     }
# }

ROOT_URLCONF = "hope_payment_gateway.config.urls"
WSGI_APPLICATION = "hope_payment_gateway.config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(PACKAGE_DIR / "templates")],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "constance.context_processors.config",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
            "libraries": {
                "staticfiles": "django.templatetags.static",
                "i18n": "django.templatetags.i18n",
            },
        },
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler", "level": "INFO"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

AUTH_USER_MODEL = "core.User"

HOST = env("HOST", default="http://localhost:8000")

CELERY_ACCEPT_CONTENT = ["pickle", "json", "application/text"]
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_VISIBILITY_VAR = env("CELERY_VISIBILITY_TIMEOUT", default=1800)  # in seconds
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": int(CELERY_BROKER_VISIBILITY_VAR)}
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
# Sensible settings for celery
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False
CELERY_TASK_IGNORE_RESULT = True
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_RESULT_EXPIRES = 600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
}

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = env("CORS_ORIGIN_ALLOW_ALL", default=False)


JWT_AUTH = {
    "JWT_VERIFY": False,  # this requires private key
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_LEEWAY": 60,
    "JWT_EXPIRATION_DELTA": datetime.timedelta(seconds=30000),
    "JWT_AUDIENCE": None,
    "JWT_ISSUER": None,
    "JWT_ALLOW_REFRESH": False,
    "JWT_REFRESH_EXPIRATION_DELTA": datetime.timedelta(days=7),
    "JWT_AUTH_HEADER_PREFIX": "JWT",
    "JWT_SECRET_KEY": SECRET_KEY,
    "JWT_DECODE_HANDLER": "rest_framework_jwt.utils.jwt_decode_handler",
    # Keys will be set in core.apps.Config.ready()
    "JWT_PUBLIC_KEY": "?",
    # 'JWT_PRIVATE_KEY': wallet.get_private(),
    # 'JWT_PRIVATE_KEY': None,
    "JWT_ALGORITHM": "RS256",
}
SENTRY_DSN = env("SENTRY_DSN", default=None)  # noqa: F405

if SENTRY_DSN:  # pragma: no cover
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # by default this is False, must be set to True so the library attaches the request data to the event
        send_default_pii=True,
        integrations=[DjangoIntegration(), CeleryIntegration()],
    )

if DEBUG:  # pragma: no cover
    INSTALLED_APPS += ("debug_toolbar",)  # noqa
    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TEMPLATE_CONTEXT": True,
    }


DEFAULT_FROM_EMAIL = "hope@unicef.org"
EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_PORT = env("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", default=False)

KEY = SOCIAL_AUTH_KEY = env("AZURE_B2C_CLIENT_ID", default=None)
SOCIAL_AUTH_SECRET = env("AZURE_B2C_CLIENT_SECRET", default=None)
SOCIAL_AUTH_TENANT_NAME = env("TENANT_NAME", default="unicefpartners")
SOCIAL_AUTH_TENANT_ID = f"{SOCIAL_AUTH_TENANT_NAME}.onmicrosoft.com"
SOCIAL_AUTH_TENANT_B2C_URL = f"{SOCIAL_AUTH_TENANT_NAME}.b2clogin.com"

SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_POLICY = env("AZURE_B2C_POLICY_NAME", default="B2C_1_UNICEF_SOCIAL_signup_signin")
SOCIAL_AUTH_USER_MODEL = "core.User"

SOCIAL_AUTH_PIPELINE = (
    "unicef_security.pipeline.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_by_email",
    "unicef_security.pipeline.create_unicef_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

USER_FIELDS = ["username", "email", "first_name", "last_name"]
USERNAME_IS_FULL_EMAIL = True

CONSTANCE_CONFIG = {
    "WESTERN_UNION_THREASHOLD": (
        10000,
        "Hourly threashold of calls to be made to Western Union API",
        int,
    ),
}

WESTERN_UNION_BASE_URL = env("WESTERN_UNION_BASE_URL")
WESTERN_UNION_PATH = env("WESTERN_UNION_PATH")
WESTERN_UNION_CERT = env("WESTERN_UNION_CERT")
WESTERN_UNION_KEY = env("WESTERN_UNION_KEY")
