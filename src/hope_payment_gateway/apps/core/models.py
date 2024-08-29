from django.contrib.auth import get_user_model
from django.db import models

from unicef_security.models import AbstractUser, SecurityMixin


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class User(SecurityMixin, AbstractUser):
    class Meta:
        app_label = "core"


class System(models.Model):
    name = models.CharField(max_length=64, unique=True)
    owner = models.OneToOneField(get_user_model(), on_delete=models.PROTECT)
    # callback_url = models.URLField(null=True, blank=True)

    class Meta:
        app_label = "core"

    def __str__(self):
        return self.name
