from django.db import models


class Corridor(models.Model):  # delivery mechanism
    description = models.CharField(max_length=1024)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.description} / {self.template_code}"