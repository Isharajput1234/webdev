from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Job


@receiver(post_save, sender=Job)
def job_posted_notify_matches(sender, instance, created, **kwargs):
    """Smart job alert: email matching seekers when a new job is posted."""
    if not created or not instance.is_active:
        return

    from apps.accounts.ai_notifications import send_job_match_alerts_for_job

    send_job_match_alerts_for_job(instance)
