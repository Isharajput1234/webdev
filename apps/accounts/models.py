from urllib.parse import quote, urlparse

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.urls import reverse

class CustomUser(AbstractUser):
    is_employer = models.BooleanField(default=False)
    is_job_seeker = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class EmailOTP(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_LOGIN = "login"
    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, "Signup"),
        (PURPOSE_LOGIN, "Login"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="email_otps")
    email = models.EmailField()
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    code_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "-created_at"]),
            models.Index(fields=["email", "purpose", "-created_at"]),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None

class Employer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    company_description = models.TextField(blank=True)
    company_website = models.URLField(blank=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.company_name

    def get_absolute_url(self):
        return reverse('accounts:employer_profile', args=[str(self.id)])

    def website_domain(self):
        raw = (self.company_website or "").strip()
        if not raw:
            return ""
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        try:
            netloc = urlparse(raw).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    @property
    def display_logo_url(self):
        if self.company_logo and getattr(self.company_logo, "name", ""):
            try:
                return self.company_logo.url
            except ValueError:
                pass
        domain = self.website_domain()
        if domain:
            return f"https://www.google.com/s2/favicons?domain={quote(domain)}&sz=128"
        name = (self.company_name or "Company").strip() or "Company"
        return (
            f"https://ui-avatars.com/api/?name={quote(name)}&size=128"
            f"&background=6366f1&color=fff&bold=true"
        )

    @property
    def job_count(self):
        return self.jobs.filter(is_active=True).count()

class JobSeeker(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/', blank=True)
    skills = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    education = models.TextField(blank=True)
    extracted_skills = models.JSONField(default=list, blank=True)
    ai_notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class JobMatchAlert(models.Model):
    """Tracks job-match emails sent (prevents duplicates)."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="job_match_alerts")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="match_alerts")
    match_score = models.FloatField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.user.username} ← {self.job.title} ({self.match_score}%)"


class UserNotification(models.Model):
    TYPE_JOB_MATCH = "job_match"
    TYPE_INACTIVE = "inactive"
    TYPE_CHOICES = [
        (TYPE_JOB_MATCH, "New job match"),
        (TYPE_INACTIVE, "Inactive reminder"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"
