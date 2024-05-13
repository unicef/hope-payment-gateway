# Generated by Django 5.0.4 on 2024-05-12 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gateway", "0015_rename_confirmation_code_paymentrecord_auth_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentrecord",
            name="payout_amount",
            field=models.DecimalField(decimal_places=2, max_digits=12, null=True),
        ),
    ]