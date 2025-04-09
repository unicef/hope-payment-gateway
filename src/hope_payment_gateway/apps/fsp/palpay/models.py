from django.db import models


class PalPayGram(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("can_prepare_payment", "PalPay: Can Prepare Transaction"),
            ("can_create_transaction", "PalPay: Can Create Transaction"),
            ("can_quote_transaction", "PalPay: Can Quote Transaction"),
            ("can_check_status", "PalPay: Can Check Status"),
            ("can_update_status", "PalPay: Can Update Status"),
            ("can_cancel_transaction", "PalPay: Can Cancel Transaction"),
        )

    def __str__(self):
        return "Fake model to represent PalPay and wrap permissions"
