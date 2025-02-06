# Generated by Django 4.2.5 on 2023-09-27 12:12

import uuid

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import strategy_field.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialServiceProvider",
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
                ("name", models.CharField(max_length=64, unique=True)),
                ("vision_vendor_number", models.CharField(max_length=100, unique=True)),
                ("strategy", strategy_field.fields.StrategyField()),
                (
                    "configuration",
                    models.JSONField(blank=True, default=dict, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PaymentInstruction",
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
                (
                    "uuid",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("unicef_id", models.CharField(db_index=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("OPEN", "Open"),
                            ("READY", "Ready"),
                            ("CLOSED", "Closed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=50,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict, null=True)),
                ("tag", models.CharField(blank=True, null=True)),
                (
                    "fsp",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="gateway.financialserviceprovider",
                    ),
                ),
                (
                    "system",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.system"),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PaymentRecord",
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
                (
                    "uuid",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("record_code", models.CharField(max_length=64)),
                ("success", models.BooleanField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("TRANSFERRED_TO_FSP", "Transferred to FSP"),
                            (
                                "TRANSFERRED_TO_BENEFICIARY",
                                "Transferred to Beneficiary",
                            ),
                            ("CANCELLED", "Cancelled"),
                            ("ERROR", "Error"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=50,
                    ),
                ),
                ("message", models.CharField(blank=True, max_length=4096, null=True)),
                ("payload", models.JSONField(blank=True, default=dict, null=True)),
                ("extra_data", models.JSONField(blank=True, default=dict, null=True)),
                (
                    "parent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="gateway.paymentinstruction",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
