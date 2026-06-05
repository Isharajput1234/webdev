from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("purpose", models.CharField(choices=[("signup", "Signup"), ("login", "Login")], max_length=20)),
                ("code_hash", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_otps", to="accounts.customuser"),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "purpose", "-created_at"], name="accounts_em_user_id_dc4b02_idx"),
                    models.Index(fields=["email", "purpose", "-created_at"], name="accounts_em_email_814cb4_idx"),
                ],
            },
        ),
    ]

