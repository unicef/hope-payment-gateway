from django.db import models


class Corridor(models.Model):  # delivery mechanism
    description = models.CharField(max_length=1024)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.description} / {self.template_code}"

    class Meta:
        unique_together = ("destination_country", "destination_currency")


class ServiceProviderCode(models.Model):
    description = models.CharField(max_length=64)
    code = models.CharField(max_length=32, unique=True)
    country = models.CharField(max_length=2)
    currency = models.CharField(max_length=3)

    def __str__(self):
        return f"{self.description}"
