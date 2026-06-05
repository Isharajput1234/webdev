from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Employer, JobSeeker, EmailOTP, JobMatchAlert, UserNotification

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_employer', 'is_job_seeker', 'is_staff')
    list_filter = ('is_employer', 'is_job_seeker', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('is_employer', 'is_job_seeker')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Employer)
admin.site.register(JobSeeker)
admin.site.register(EmailOTP)


@admin.register(JobMatchAlert)
class JobMatchAlertAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "match_score", "sent_at")
    list_filter = ("sent_at",)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "email_sent", "is_read", "created_at")
    list_filter = ("notification_type", "email_sent", "is_read")
