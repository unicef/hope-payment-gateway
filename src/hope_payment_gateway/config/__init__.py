from smart_env import SmartEnv

MANDATORY = {
    "DATABASE_URL": (str, "", "Database connetcion url"),
    "SECRET_KEY": (str, ""),
    "CACHE_URL": (str, "redis://localhost:6379/0"),
    "CELERY_BROKER_URL": (str, "redis://localhost:6379/0"),
}

DEVELOPMENT = {
    "DEBUG": (bool, True),
    "AUTHENTICATION_BACKENDS": (list, []),
    "SECURE_SSL_REDIRECT": (bool, False),
    "SECURE_HSTS_PRELOAD": (bool, False),
    "CSRF_COOKIE_SECURE": (bool, False),
    "SESSION_COOKIE_SECURE": (bool, False),
}

OPTIONAL = {
    "ADMIN_EMAIL": (str, "", "Admin email"),
    "ADMIN_PASSWORD": (str, "", "Admin password"),
    "ALLOWED_HOSTS": (list, ["127.0.0.1", "localhost"]),
    "AZURE_ACCOUNT_KEY": (str, ""),
    "AZURE_ACCOUNT_NAME": (str, ""),
    "AZURE_CONTAINER": (str, ""),
    "AZURE_CLIENT_KEY": (str, ""),
    "AZURE_CLIENT_SECRET": (str, ""),
    "AZURE_TENANT_ID": (str, ""),
    "CELERY_VISIBILITY_TIMEOUT": (int, 1800),
    "CELERY_TASK_ALWAYS_EAGER": (bool, False),
    "CELERY_TASK_EAGER_PROPAGATES": (bool, True),
    "CORS_ORIGIN_ALLOW_ALL": (bool, False),
    "CSRF_COOKIE_SECURE": (bool, True),
    "DEFAULT_FROM_EMAIL": (str, ""),
    "DEBUG": (bool, False, "Django DEBUG"),
    "EMAIL_HOST": (str, ""),
    "EMAIL_HOST_PASSWORD": (str, ""),
    "EMAIL_HOST_USER": (str, ""),
    "EMAIL_PORT": (int, 587),
    "EMAIL_USE_SSL": (bool, False),
    "EMAIL_USE_TLS": (bool, True),
    "FILE_STORAGE_DEFAULT": (str, "django.core.files.storage.FileSystemStorage"),
    "FILE_STORAGE_MEDIA": (str, "django.core.files.storage.FileSystemStorage"),
    "FILE_STORAGE_STATIC": (
        str,
        "django.contrib.staticfiles.storage.StaticFilesStorage",
    ),
    "FTP_WESTERN_UNION_PASSWORD": (str, ""),
    "FTP_WESTERN_UNION_PORT": (int, 22),
    "FTP_WESTERN_UNION_SERVER": (str, ""),
    "FTP_WESTERN_UNION_USERNAME": (str, ""),
    "HOST": (str, "http://localhost:8000"),
    "LOGIN_ENABLED": (bool, False),
    "SECURE_HSTS_SECONDS": (int, 60),
    "SESSION_COOKIE_HTTPONLY": (bool, True),
    "SECURE_SSL_REDIRECT": (bool, True),
    "SECURE_HSTS_PRELOAD": (bool, True),
    "SIGNING_BACKEND": (str, "django.core.signing.TimestampSigner"),
    "MEDIA_URL": (str, "/media/"),
    "MEDIA_ROOT": (str, "/tmp/media/"),  # noqa
    "MONEYGRAM_HOST": (str, ""),
    "MONEYGRAM_CLIENT_ID": (str, ""),
    "MONEYGRAM_CLIENT_SECRET": (str, ""),
    "MONEYGRAM_REGISTRATION_NUMBER": (str, ""),
    "MONEYGRAM_PUBLIC_KEY": (str, ""),
    "SENTRY_DSN": (str, ""),
    "SENTRY_ENVIRONMENT": (str, ""),
    "SENTRY_URL": (str, "https://monitoring.hope.unicef.org/"),
    "SESSION_COOKIE_DOMAIN": (str, "unicef.org"),
    "SESSION_COOKIE_NAME": (str, "hpg_session"),
    "SESSION_COOKIE_PATH": (str, "/"),
    "SESSION_COOKIE_SECURE": (bool, True),
    "STATIC_URL": (str, "/static/"),
    "STATIC_ROOT": (str, "/tmp/static/"),  # noqa
    "SUPERUSERS": (str, ""),
    "TIME_ZONE": (str, "UTC"),
    "WESTERN_UNION_BASE_URL": (str, ""),
    "WESTERN_UNION_CERT": (str, ""),
    "WESTERN_UNION_KEY": (str, ""),
    "WP_APPLICATION_SERVER_KEY": (str, ""),
    "WP_CLAIMS": (
        str,
        '{"sub": "mailto: hope@unicef.org","aud": "https://android.googleapis.com"}',
    ),
    "WP_PRIVATE_KEY": (str, ""),
}


env = SmartEnv(**{**DEVELOPMENT, **MANDATORY, **OPTIONAL})  # type: ignore[no-untyped-call]
