import binascii
import os
from enum import Enum, auto, unique
from typing import Any

import swapper
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .fields import ChoiceArrayField


@unique
class Grant(Enum):
    def _generate_next_value_(self, start: int, count: int, last_values: list[Any]) -> Any:
        return self

    API_READ_ONLY = auto()
    API_PLAN_UPLOAD = auto()
    API_PLAN_MANAGE = auto()

    @classmethod
    def choices(cls) -> tuple[tuple[Any, Any], ...]:
        return tuple((i.value, i.value) for i in cls)


class AbstractAPIToken(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    key = models.CharField(_("Key"), max_length=40, unique=True, blank=True)  # token
    allowed_ips = models.CharField(_("IPs"), max_length=200, blank=True, null=True)

    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(blank=True, null=True)

    grants = ChoiceArrayField(models.CharField(choices=Grant.choices(), max_length=255))

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"Token #{self.pk}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls) -> str:
        return binascii.hexlify(os.urandom(20)).decode()


class APIToken(AbstractAPIToken):
    class Meta:
        swappable = swapper.swappable_setting("hope_api_auth", "APIToken")


class APILogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    token = models.ForeignKey(APIToken, on_delete=models.PROTECT)
    url = models.URLField()
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.token} {self.method} {self.timestamp}"
