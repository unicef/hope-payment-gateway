# Generated by Django 5.0.4 on 2024-04-23 06:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0013_deliverymechanism_financialserviceprovider_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentrecord",
            name="confirmation_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                help_text="MTCN for western union, reference number for MoneyGram",
            ),
        ),
    ]
