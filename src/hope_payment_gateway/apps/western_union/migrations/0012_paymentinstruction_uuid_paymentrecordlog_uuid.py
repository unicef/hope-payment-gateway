# Generated by Django 4.2.4 on 2023-09-19 15:22

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("western_union", "0011_paymentrecordlog_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentinstruction",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="paymentrecordlog",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
