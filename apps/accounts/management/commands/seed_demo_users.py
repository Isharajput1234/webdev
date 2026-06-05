from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Employer, JobSeeker


class Command(BaseCommand):
    help = "Create demo users for OTP testing (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Test@12345",
            help="Password to set for demo accounts (default: Test@12345)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        User = get_user_model()

        # Note: user provided some typos like gamil/gamail; using corrected gmail.com where obvious.
        demo = [
            # job seekers
            ("atulya", "atulya.saxena2005@gmail.com", "job_seeker"),
            ("radhika", "radhikagarg933@gmail.com", "job_seeker"),
            ("niharika", "aggl.niharikss@gmail.com", "job_seeker"),
            # isha should exist as employer (and can be job seeker too if you want)
            ("isha_rajput", "isharajput9411@gmail.com", "employer_and_job_seeker"),
        ]

        for username, email, role in demo:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_active": True},
            )

            changed = False
            if user.email != email:
                user.email = email
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True

            if role == "job_seeker":
                if not user.is_job_seeker:
                    user.is_job_seeker = True
                    changed = True
                if user.is_employer:
                    user.is_employer = False
                    changed = True
            elif role == "employer":
                if not user.is_employer:
                    user.is_employer = True
                    changed = True
                if user.is_job_seeker:
                    user.is_job_seeker = False
                    changed = True
            else:
                # both roles
                if not user.is_employer:
                    user.is_employer = True
                    changed = True
                if not user.is_job_seeker:
                    user.is_job_seeker = True
                    changed = True

            if created:
                user.set_password(password)
                changed = True

            if changed:
                user.save()

            if role == "job_seeker":
                JobSeeker.objects.get_or_create(user=user)
                self.stdout.write(self.style.SUCCESS(f"Job seeker ready: {username} ({email})"))
            elif role == "employer":
                Employer.objects.get_or_create(
                    user=user,
                    defaults={
                        "company_name": "Isha Company",
                        "company_description": "Demo employer account",
                    },
                )
                self.stdout.write(self.style.SUCCESS(f"Employer ready: {username} ({email})"))
            else:
                Employer.objects.get_or_create(
                    user=user,
                    defaults={
                        "company_name": "Isha Company",
                        "company_description": "Demo employer account",
                    },
                )
                JobSeeker.objects.get_or_create(user=user)
                self.stdout.write(self.style.SUCCESS(f"Employer + job seeker ready: {username} ({email})"))

        self.stdout.write(self.style.SUCCESS(f"Done. Password for new demo users: {password}"))

