# Generated by Django 5.0.4 on 2024-04-11 21:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("western_union", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="corridor",
            unique_together={("destination_country", "destination_currency")},
        ),
    ]
