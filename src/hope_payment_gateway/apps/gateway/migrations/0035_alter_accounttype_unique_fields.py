# Generated by Django 5.1.6 on 2025-03-26 15:06

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0034_alter_financialserviceproviderconfig_required_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accounttype",
            name="unique_fields",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=255),
                blank=True,
                default=list,
                help_text="comma separated list of unique fields",
                null=True,
                size=None,
            ),
        ),
    ]
