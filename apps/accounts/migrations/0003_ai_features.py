from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
        ("accounts", "0002_emailotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseeker",
            name="extracted_skills",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="jobseeker",
            name="ai_notifications_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="JobMatchAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("match_score", models.FloatField(default=0)),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="match_alerts",
                        to="jobs.job",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_match_alerts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-sent_at"],
                "unique_together": {("user", "job")},
            },
        ),
    ]
