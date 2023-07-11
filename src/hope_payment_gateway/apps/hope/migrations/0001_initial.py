# Generated by Django 4.2.3 on 2023-07-11 09:44

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BusinessArea",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("slug", models.CharField(db_index=True, max_length=250, unique=True)),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "db_table": "core_businessarea",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="FinancialServiceProvider",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "communication_channel",
                    models.CharField(
                        choices=[("API", "API"), ("SFTP", "SFTP"), ("XLSX", "XLSX")], db_index=True, max_length=6
                    ),
                ),
            ],
            options={
                "db_table": "payment_financialserviceprovider",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="PaymentPlan",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("status", models.TextField()),
                ("dispersion_start_date", models.DateField()),
                ("dispersion_end_date", models.DateField()),
                ("start_date", models.DateTimeField(db_index=True)),
                ("end_date", models.DateTimeField(db_index=True)),
                (
                    "total_entitled_quantity",
                    models.DecimalField(db_index=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "total_entitled_quantity_usd",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                ("is_follow_up", models.BooleanField(default=False)),
                (
                    "total_delivered_quantity",
                    models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "total_delivered_quantity_usd",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "total_undelivered_quantity",
                    models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "total_undelivered_quantity_usd",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
            ],
            options={
                "db_table": "payment_paymentplan",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="PaymentRecord",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Distribution Successful", "Distribution Successful"),
                            ("Not Distributed", "Not Distributed"),
                            ("Transaction Successful", "Transaction Successful"),
                            ("Transaction Erroneous", "Transaction Erroneous"),
                            ("Force failed", "Force failed"),
                            ("Partially Distributed", "Partially Distributed"),
                            ("Pending", "Pending"),
                        ],
                        default="Pending",
                        max_length=255,
                    ),
                ),
                ("conflicted", models.BooleanField(default=False)),
                ("excluded", models.BooleanField(default=False)),
                ("entitlement_date", models.DateTimeField(blank=True, null=True)),
                ("is_follow_up", models.BooleanField(default=False)),
                ("delivery_type", models.CharField(max_length=24, null=True)),
                ("entitlement_quantity", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                (
                    "entitlement_quantity_usd",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                ("delivered_quantity", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("delivered_quantity_usd", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("delivery_date", models.DateTimeField(blank=True, null=True)),
                ("transaction_reference_id", models.CharField(max_length=255, null=True)),
            ],
            options={
                "db_table": "payment_payment",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Programme",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("DRAFT", "Draft"), ("FINISHED", "Finished")],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(db_index=True)),
            ],
            options={
                "db_table": "program_program",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ProgrammeCycle",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("iteration", models.PositiveIntegerField()),
                ("status", models.CharField(max_length=10)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "db_table": "program_programcycle",
                "managed": False,
            },
        ),
    ]
