from ..settings import env

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = env("CORS_ORIGIN_ALLOW_ALL", default=False)
