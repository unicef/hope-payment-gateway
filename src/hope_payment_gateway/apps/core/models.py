from django.contrib.auth import get_user_model
from django.db import models

from unicef_security.models import AbstractUser, SecurityMixin


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
