from abc import ABCMeta
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from unicef_security.models import AbstractUser, SecurityMixin, TimeStampedModel


class Singleton(ABCMeta):
    """Metaclass that ensures only one instance exists per class."""

    _instances: dict[type, object] = {}

    # `cls._instances` (not `Singleton._instances`) is required so that
    # `SubClass._instances = {}` can reset the cache, which the tests rely on.
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class User(TimeStampedModel, SecurityMixin, AbstractUser):  # type: ignore[misc]
    class Meta:
        app_label = "core"


class System(models.Model):
    name = models.CharField(max_length=64, unique=True)
    owner = models.OneToOneField(get_user_model(), on_delete=models.PROTECT)

    class Meta:
        app_label = "core"
        permissions = (("can_access_ftp", "Can access files from FTP"),)

    def __str__(self) -> str:
        return self.name
