# Generated by Django 4.2.10 on 2024-03-29 10:14

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("gateway", "0009_alter_paymentrecord_record_code"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="paymentinstruction",
            unique_together={("system", "remote_id")},
        ),
    ]
