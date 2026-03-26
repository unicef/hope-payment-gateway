from django.conf import settings
import typing

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import User


def set_superusers(user: User | None = None, is_new: bool = False, **kwargs: dict) -> dict:
    if user and is_new and user.email in settings.SUPERUSERS:
        user.is_superuser = True
        user.save()
    return {}
