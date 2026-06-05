import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print non-secret email configuration (for debugging OTP delivery)."

    def handle(self, *args, **options):
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', '')}")
        self.stdout.write(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', '')}")
        self.stdout.write(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', '')}")
        self.stdout.write(f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', '')}")
        self.stdout.write(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '')}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")
        self.stdout.write(f"DJANGO_EMAIL_DEBUG env: {os.environ.get('DJANGO_EMAIL_DEBUG', '')}")
