# Generated by Django 4.2.5 on 2023-09-26 10:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_system"),
    ]

    operations = [
        migrations.AlterField(
            model_name="system",
            name="name",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
