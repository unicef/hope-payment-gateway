# Generated by Django 5.1.3 on 2024-11-06 13:10

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "gateway",
            "0024_rename_vision_vendor_number_financialserviceprovider_vendor_number",
        ),
    ]

    operations = [
        migrations.RenameField(
            model_name="paymentinstruction",
            old_name="unicef_id",
            new_name="external_code",
        ),
    ]
