from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a test email using current EMAIL_BACKEND/SMTP settings."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient email")

    def handle(self, *args, **options):
        to = options["to"]
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', '')}")
        self.stdout.write(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', '')}")
        self.stdout.write(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '')}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")

        send_mail(
            "Test email from Job Portal",
            "If you received this, SMTP is working.",
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS("Sent. (If console backend, check terminal output.)"))

