from abc import ABCMeta

from django.contrib.auth import get_user_model
from django.db import models
from unicef_security.models import AbstractUser, SecurityMixin, TimeStampedModel


class Singleton(ABCMeta):
    """Metaclass that ensures only one instance exists per class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class User(TimeStampedModel, SecurityMixin, AbstractUser):
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
