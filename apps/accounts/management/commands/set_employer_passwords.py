from django.core.management.base import BaseCommand

from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = "Set the same password for every user with is_employer=True (uses Django hashing)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="one",
            help='New password for all employer accounts (default: "one").',
        )

    def handle(self, *args, **options):
        pw = options["password"]
        qs = CustomUser.objects.filter(is_employer=True)
        count = 0
        for user in qs.iterator():
            user.set_password(pw)
            user.save(update_fields=["password"])
            count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Updated password for {count} employer account(s) to {pw!r}.")
        )
