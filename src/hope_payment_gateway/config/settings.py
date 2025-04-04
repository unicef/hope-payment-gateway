import os
from pathlib import Path
from urllib.parse import urlparse

from . import env

SETTINGS_DIR = Path(__file__).parent
PACKAGE_DIR = SETTINGS_DIR.parent
DEVELOPMENT_DIR = PACKAGE_DIR.parent.parent

DEBUG = env.bool("DEBUG")

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

INSTALLED_APPS = (
    "hope_payment_gateway.web",
    "hope_payment_gateway.apps.core.apps.AppConfig",
    "hope_payment_gateway.apps.gateway.apps.AppConfig",
    "hope_payment_gateway.apps.fsp.western_union.apps.AppConfig",
    "hope_payment_gateway.apps.fsp.moneygram.apps.AppConfig",
    "hope_api_auth",
    "unicef_security",
    "django.contrib.contenttypes",
    "advanced_filters",
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
    "jsoneditor",
    "corsheaders",
    "viewflow",
    "social_django",
    "admin_extra_buttons",
    "adminactions",
    "adminfilters",
    "adminfilters.depot",
    "smart_env",
    "smart_admin.apps.SmartTemplateConfig",
    "import_export",
    "constance",
    "rest_framework",
    "django_celery_beat",
    "django_celery_results",
    "django_celery_boost",
    "drf_spectacular",
    "drf_spectacular_sidecar",
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
    "social_core.backends.azuread_tenant.AzureADTenantOAuth2",
    "django.contrib.auth.backends.ModelBackend",
    *env("AUTHENTICATION_BACKENDS"),
)


# path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
MEDIA_ROOT = env("MEDIA_ROOT")
MEDIA_URL = env("MEDIA_URL")
STATIC_ROOT = env("STATIC_ROOT")
STATIC_URL = env("STATIC_URL")
STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STORAGES = {
    "default": env.storage("FILE_STORAGE_DEFAULT"),
    "staticfiles": env.storage("FILE_STORAGE_STATIC"),
    "media": env.storage("FILE_STORAGE_MEDIA"),
}

SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = ("*",)

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_URL = "/accounts/logout"
LOGOUT_REDIRECT_URL = "/"

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


CACHE_URL = env("CACHE_URL")
REDIS_URL = urlparse(CACHE_URL).hostname
CACHES = {
    "default": {
        "BACKEND": "redis_lock.django_cache.RedisCache",
        "LOCATION": CACHE_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

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

HOST = env("HOST")


DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = env(
    "EMAIL_HOST",
)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_USE_SSL = env("EMAIL_USE_SSL")

LOGIN_ENABLED = env("LOGIN_ENABLED")

SUPERUSERS = env("SUPERUSERS").split(",")
from .fragments import *  # noqa
