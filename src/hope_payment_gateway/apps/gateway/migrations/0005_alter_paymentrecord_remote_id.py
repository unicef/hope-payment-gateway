# Generated by Django 4.2.8 on 2024-01-09 15:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0004_remove_paymentinstruction_uuid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentrecord",
            name="remote_id",
            field=models.CharField(db_index=True, max_length=255, unique=True),
        ),
    ]
