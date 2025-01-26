from django.db import models


class Corridor(models.Model):  # delivery mechanism
    description = models.CharField(max_length=1024)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        unique_together = ("destination_country", "destination_currency")
        permissions = (
            ("das_countries_currencies", "Western Union DAS: Country/Currency"),
            ("das_origination_currencies", "Western Union DAS: Origination Currencies"),
            ("das_destination_currencies", "Western Union DAS: Destination Currencies"),
            ("das_destination_countries", "Western Union DAS: Destination Countries"),
            ("das_delivery_services", "Western Union DAS: Delivery Services"),
            ("das_delivery_option_template", "Western Union DAS: Delivery Option Template"),
            ("can_prepare_transaction", "Western Union: Can Prepare Transaction"),
            ("can_create_transaction", "Western Union: Can Create Transaction"),
            ("can_check_status", "Western Union: Can Check Status"),
            ("can_update_status", "Western Union: Can Update Status"),
            ("can_search_request", "Western Union: Can Search Request"),
            ("can_cancel_transaction", "Western Union: Can Cancel Transaction"),
            ("can_view_ftp_files", "Western Union DAS: Can views Western Union FTP files"),
        )

    def __str__(self) -> str:
        return f"{self.description} / {self.template_code}"


class ServiceProviderCode(models.Model):
    description = models.CharField(max_length=64)
    code = models.CharField(max_length=32, unique=True)
    country = models.CharField(max_length=2)
    currency = models.CharField(max_length=3)

    def __str__(self) -> str:
        return f"{self.description}"
