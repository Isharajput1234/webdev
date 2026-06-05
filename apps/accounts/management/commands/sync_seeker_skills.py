from django.core.management.base import BaseCommand

from apps.accounts.models import JobSeeker
from apps.accounts.ai_engine import sync_seeker_skills


class Command(BaseCommand):
    help = "Extract and cache skills from all job seeker profiles/resumes."

    def handle(self, *args, **options):
        for seeker in JobSeeker.objects.select_related("user"):
            skills = sync_seeker_skills(seeker)
            self.stdout.write(f"{seeker.user.username}: {', '.join(skills) or '(none)'}")
