# Generated by Django 5.0.4 on 2024-04-16 09:33

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0012_alter_financialserviceproviderconfig_fsp"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryMechanism",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("code", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="financialserviceprovider",
            name="created",
            field=model_utils.fields.AutoCreatedField(
                default=django.utils.timezone.now,
                editable=False,
                verbose_name="created",
            ),
        ),
        migrations.AddField(
            model_name="financialserviceprovider",
            name="modified",
            field=model_utils.fields.AutoLastModifiedField(
                default=django.utils.timezone.now,
                editable=False,
                verbose_name="modified",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="financialserviceproviderconfig",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="financialserviceproviderconfig",
            name="delivery_mechanism",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fsp",
                to="gateway.deliverymechanism",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="financialserviceproviderconfig",
            unique_together={("key", "fsp", "delivery_mechanism")},
        ),
    ]
