from django.db import models


class MoneyGram(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("can_prepare_payment", "MoneyGram: Can Prepare Transaction"),
            ("can_create_transaction", "MoneyGram: Can Create Transaction"),
            ("can_quote_transaction", "MoneyGram: Can Quote Transaction"),
            ("can_check_status", "MoneyGram: Can Check Status"),
            ("can_update_status", "MoneyGram: Can Update Status"),
            ("can_cancel_transaction", "MoneyGram: Can Cancel Transaction"),
        )

    def __str__(self):
        return "Fake model to represent Moneygram and wrap permissions"
