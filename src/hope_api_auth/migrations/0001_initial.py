# Generated by Django 4.2.4 on 2023-09-23 01:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import hope_api_auth.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="APIToken",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(blank=True, max_length=40, unique=True, verbose_name="Key")),
                ("allowed_ips", models.CharField(blank=True, max_length=200, null=True, verbose_name="IPs")),
                ("valid_from", models.DateField(default=django.utils.timezone.now)),
                ("valid_to", models.DateField(blank=True, null=True)),
                (
                    "grants",
                    hope_api_auth.fields.ChoiceArrayField(
                        base_field=models.CharField(
                            choices=[
                                ("API_READ_ONLY", "API_READ_ONLY"),
                                ("API_PLAN_UPLOAD", "API_PLAN_UPLOAD"),
                                ("API_PLAN_MANAGE", "API_PLAN_MANAGE"),
                            ],
                            max_length=255,
                        ),
                        size=None,
                    ),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "swappable": "HOPE_API_AUTH_APITOKEN_MODEL",
            },
        ),
        migrations.CreateModel(
            name="APILogEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("url", models.URLField()),
                ("method", models.CharField(max_length=10)),
                ("status_code", models.IntegerField()),
                (
                    "token",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.HOPE_API_AUTH_APITOKEN_MODEL
                    ),
                ),
            ],
        ),
    ]