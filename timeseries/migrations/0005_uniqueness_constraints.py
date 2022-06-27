# Generated by Django 3.1.13 on 2022-06-07 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timeseries", "0004_measurement_summaries"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="measurement",
            constraint=models.UniqueConstraint(
                condition=models.Q(flag_id__isnull=False),
                fields=(
                    "name",
                    "owner_id",
                    "repo_id",
                    "flag_id",
                    "commit_sha",
                    "timestamp",
                ),
                name="timeseries_measurement_flag_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="measurement",
            constraint=models.UniqueConstraint(
                condition=models.Q(flag_id__isnull=True),
                fields=("name", "owner_id", "repo_id", "commit_sha", "timestamp"),
                name="timeseries_measurement_noflag_unique",
            ),
        ),
    ]
