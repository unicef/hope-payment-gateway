from django.db import models

from model_utils.models import TimeStampedModel


class Corridor(models.Model):  # delivery mechanism
    description = models.CharField(max_length=1024)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.description} / {self.template_code}"

    # example_dict = {
    #     "wallet_details": {
    #         "service_provider_code": ["06301", "06302", "06304"]
    #     },
    #     "receiver": {
    #         "mobile_phone": {
    #             "phone_number": {
    #                 "country_code": 63,
    #                 "national_number": None
    #             }
    #         },
    #         "reason_for_sending": ["P012", "P020", "P014"]
    #     }
    # }


class PaymentRecordLog(TimeStampedModel):
    record_code = models.CharField(max_length=64)
    success = models.BooleanField(null=True, blank=True)
    message = models.CharField(max_length=1024, null=True, blank=True)
    payload = models.JSONField(default=dict)
    extra_data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.record_code} / {self.message}"
