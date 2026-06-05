"""
Email notifications for job matches and inactive users.
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta

from apps.jobs.models import Job
from apps.accounts.models import JobSeeker, JobMatchAlert, CustomUser, UserNotification
from apps.accounts.ai_engine import (
    get_job_recommendations,
    combined_match_score,
    sync_seeker_skills,
)


def _site_url():
    return getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def _threshold():
    return float(getattr(settings, "AI_MATCH_THRESHOLD", 80))


def create_user_notification(user, ntype: str, title: str, message: str, link: str = "", email_sent: bool = False):
    return UserNotification.objects.create(
        user=user,
        notification_type=ntype,
        title=title,
        message=message,
        link=link,
        email_sent=email_sent,
    )


def inactive_days(user) -> int | None:
    if not user.last_login:
        return None
    return (timezone.now() - user.last_login).days


def send_email_to_user(user, subject: str, template: str, context: dict):
    if not user.email:
        return False
    if not getattr(user.jobseeker, "ai_notifications_enabled", True):
        return False
    context["site_url"] = _site_url()
    context["user"] = user
    body = render_to_string(template, context)
    html = render_to_string(template.replace(".txt", ".html"), context)
    try:
        from django.core.mail import EmailMultiAlternatives

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return True


def send_job_match_alerts_for_job(job: Job):
    """When HR posts a job, email seekers with similarity >= threshold."""
    if not job.is_active:
        return 0

    seekers = JobSeeker.objects.select_related("user").filter(
        user__is_active=True,
        user__is_job_seeker=True,
        ai_notifications_enabled=True,
    )
    sent = 0
    job_blob = f"{job.title} {job.description} {job.requirements}"

    for seeker in seekers:
        if not seeker.user.email:
            continue
        if JobMatchAlert.objects.filter(user=seeker.user, job=job).exists():
            continue

        sync_seeker_skills(seeker, save=True)
        score = combined_match_score(seeker, job)
        if score < _threshold():
            continue

        job_url = f"{_site_url()}/jobs/{job.id}/"
        title = f"New job: {job.title} at {job.employer.company_name}"
        msg = f"{score}% skill match — {job.title} at {job.employer.company_name}. Apply now!"
        create_user_notification(
            seeker.user,
            UserNotification.TYPE_JOB_MATCH,
            title,
            msg,
            link=job_url,
            email_sent=False,
        )
        ok = send_email_to_user(
            seeker.user,
            f"New job match ({score}%): {job.title}",
            "accounts/emails/job_match.txt",
            {
                "job": job,
                "score": score,
                "employer_name": job.employer.company_name,
                "job_url": job_url,
            },
        )
        if ok:
            JobMatchAlert.objects.create(user=seeker.user, job=job, match_score=score)
            UserNotification.objects.filter(
                user=seeker.user,
                title=title,
                notification_type=UserNotification.TYPE_JOB_MATCH,
            ).update(email_sent=True)
            sent += 1
    return sent


def send_inactive_user_reminders():
    """
    7 days inactive: digest of new matching jobs.
    15 days inactive: personalized top recommendations.
    """
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=15)

    seekers = JobSeeker.objects.select_related("user").filter(
        user__is_active=True,
        user__is_job_seeker=True,
        ai_notifications_enabled=True,
    )
    sent = 0
    active_jobs = list(Job.objects.filter(is_active=True))

    for seeker in seekers:
        user = seeker.user
        if not user.email:
            continue
        last = user.last_login
        if last is None:
            continue

        sync_seeker_skills(seeker, save=True)
        recs = get_job_recommendations(seeker, active_jobs, min_score=50)[:10]

        days = inactive_days(user) or 0

        if last <= two_weeks_ago and recs:
            top = recs[:5]
            companies = ", ".join({r["job"].employer.company_name for r in top})
            create_user_notification(
                user,
                UserNotification.TYPE_INACTIVE,
                f"Inactive {days} days — {len(top)} jobs for you",
                f"Personalized picks at: {companies}. Log in to apply.",
                link=f"{_site_url()}/accounts/ai/recommendations/",
            )
            ok = send_email_to_user(
                user,
                f"Your personalized job picks — {len(top)} roles for you",
                "accounts/emails/inactive_15d.txt",
                {"recommendations": top, "days": days},
            )
            if ok:
                sent += 1
        elif last <= week_ago and recs:
            recent = [r for r in recs if r["score"] >= _threshold()][:5]
            if not recent:
                recent = recs[:5]
            create_user_notification(
                user,
                UserNotification.TYPE_INACTIVE,
                f"Inactive {days} days — {len(recent)} matching jobs",
                "New roles match your skills. Check AI Job Matches.",
                link=f"{_site_url()}/accounts/ai/recommendations/",
            )
            ok = send_email_to_user(
                user,
                f"{len(recent)} new jobs matching your profile",
                "accounts/emails/inactive_7d.txt",
                {"recommendations": recent, "days": days},
            )
            if ok:
                sent += 1
    return sent
