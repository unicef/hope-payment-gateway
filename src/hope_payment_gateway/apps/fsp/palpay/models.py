from django.db import models


class PalPayGram(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("can_check_profile", "PalPay: Can Check Profiles"),
            ("can_check_balance", "PalPay: Can Check Balance"),
            ("can_check_beneficiary", "PalPay: Can Check Beneficiary"),
            ("can_check_transactions", "PalPay: Can Check Transactions"),
            ("can_create_transaction", "PalPay: Can Create Transactions"),
            ("can_check_status", "PalPay: Can Check Transaction Status"),
            ("can_update_status", "PalPay: Can Update Transaction Status"),
        )

    def __str__(self):
        return "Fake model to represent PalPay and wrap permissions"
