# Generated by Django 4.2.4 on 2023-09-19 12:16

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):
    dependencies = [
        ("western_union", "0010_paymentrecordlog_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentrecordlog",
            name="status",
            field=django_fsm.FSMField(
                choices=[
                    ("PENDING", "Pending"),
                    ("VALIDATION_OK", "Validation OK"),
                    ("TRANSFERRED_TO_FSP", "Transferred to FSP"),
                    ("TRANSFERRED_TO_BENEFICIARY", "Transferred to Beneficiary"),
                    ("CANCELLED", "Cancelled"),
                    ("ERROR", "Error"),
                ],
                db_index=True,
                default="PENDING",
                max_length=50,
            ),
        ),
    ]
