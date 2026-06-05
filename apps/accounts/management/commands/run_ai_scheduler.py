from django.core.management.base import BaseCommand

from apps.accounts.ai_notifications import send_inactive_user_reminders


class Command(BaseCommand):
    help = "Run AI email tasks: inactive user reminders (schedule daily via cron/Task Scheduler)."

    def handle(self, *args, **options):
        count = send_inactive_user_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} inactive-user reminder email(s)."))
