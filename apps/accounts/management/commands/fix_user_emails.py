from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


def normalize_email(email: str) -> str:
    if not email:
        return email
    e = email.strip().lower()
    e = e.replace("@gamil.com", "@gmail.com").replace("@gamail.com", "@gmail.com")
    return e


class Command(BaseCommand):
    help = "Fix common email typos and set specific demo emails."

    def handle(self, *args, **options):
        User = get_user_model()

        # Set the exact requested users/emails (with normalization)
        desired = {
            "isha_rajput": "isharajput9411@gamil.com",
            "atulya": "atulya.saxena2005@gamail.com",
            "radhika": "radhikagarg933@gmail.com",
            "niharika": "aggl.niharikss@gmail.com",
        }

        updated = 0

        for username, raw_email in desired.items():
            email = normalize_email(raw_email)
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Missing user: {username}"))
                continue

            if user.email != email:
                user.email = email
                user.save(update_fields=["email"])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Updated {username} email → {email}"))
            else:
                self.stdout.write(f"No change for {username} ({email})")

        # Also normalize any other users with typos
        for user in User.objects.exclude(email=""):
            fixed = normalize_email(user.email)
            if fixed != user.email:
                user.email = fixed
                user.save(update_fields=["email"])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Normalized {user.username} → {fixed}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Total updated: {updated}"))

