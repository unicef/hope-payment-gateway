from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0047_alter_exporttemplate_strategy"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="financialserviceproviderconfig",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="financialserviceproviderconfig",
            constraint=models.UniqueConstraint(
                fields=["country", "fsp", "delivery_mechanism"],
                name="uniq_fsp_config_country_fsp_dm",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="exporttemplate",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="exporttemplate",
            constraint=models.UniqueConstraint(
                fields=["fsp", "config_key"],
                name="uniq_export_template_fsp_config_key",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="paymentinstruction",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="paymentinstruction",
            constraint=models.UniqueConstraint(
                fields=["system", "remote_id"],
                name="uniq_payment_instruction_system_remote_id",
            ),
        ),
    ]
