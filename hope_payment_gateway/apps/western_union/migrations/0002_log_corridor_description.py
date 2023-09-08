# Generated by Django 4.2.4 on 2023-09-04 10:52

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):
    dependencies = [
        ("western_union", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Log",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("transaction_number", models.CharField(max_length=32)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="corridor",
            name="description",
            field=models.CharField(default="corridor", max_length=1024),
            preserve_default=False,
        ),
    ]