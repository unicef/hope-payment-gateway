from django.db import models


class Corridor(models.Model):
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict)

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
