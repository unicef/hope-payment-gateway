# Generated by Django 4.2.10 on 2024-02-23 17:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0008_paymentrecord_fsp_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentrecord",
            name="record_code",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
