# Generated by Django 5.2.3 on 2025-06-19 09:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0043_alter_deliverymechanism_account_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="paymentrecord",
            old_name="extra_data",
            new_name="fsp_data",
        ),
        migrations.RemoveField(
            model_name="paymentinstruction",
            name="extra",
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="message",
            field=models.CharField(
                blank=True,
                help_text="Help Text message from latest FSP call",
                max_length=4096,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="payout_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Amount paid by FSP",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="payout_date",
            field=models.DateField(blank=True, help_text="Date of payout from FSP", null=True),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="record_code",
            field=models.CharField(
                db_index=True,
                help_text="Payment record code",
                max_length=64,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="remote_id",
            field=models.CharField(db_index=True, help_text="Remote system ID", max_length=255, unique=True),
        ),
    ]
