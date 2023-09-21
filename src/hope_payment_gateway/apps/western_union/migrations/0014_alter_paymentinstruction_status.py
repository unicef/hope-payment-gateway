# Generated by Django 4.2.4 on 2023-09-20 19:47

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):
    dependencies = [
        ("western_union", "0013_alter_paymentinstruction_uuid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentinstruction",
            name="status",
            field=django_fsm.FSMField(
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
    ]
