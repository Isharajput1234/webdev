from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
import random
from datetime import timedelta
from .forms import (
    EmployerSignUpForm,
    JobSeekerSignUpForm,
    JobSeekerUpdateForm,
    EmployerUpdateForm,
)
from .models import CustomUser, JobSeeker, Employer, EmailOTP
from apps.jobs.models import Application, Job  # Added Job model import
from .ai_engine import (
    get_job_recommendations,
    get_company_recommendations,
    get_seeker_skills,
    sync_seeker_skills,
    skill_gap_for_job,
    ats_compatibility_score,
    market_missing_skills,
)
from .ai_notifications import inactive_days
from .models import UserNotification
from .career_chat import get_career_chat_reply
from .resume_analyzer import (
    analyze_resume,
    build_improved_draft,
    build_resume_text,
    analysis_to_dict,
)
from .forms import ResumeAnalyzerForm
from django.http import HttpResponse, FileResponse, JsonResponse
from django.urls import reverse
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST
from functools import wraps
import json

OTP_TTL_MINUTES = 10
OTP_MIN_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


def _generate_otp_code():
    return f"{random.randint(0, 999999):06d}"

def _normalize_email(email: str) -> str:
    if not email:
        return email
    e = email.strip().lower()
    e = e.replace("@gamil.com", "@gmail.com").replace("@gamail.com", "@gmail.com")
    return e


def _otp_uses_console() -> bool:
    return "console" in getattr(settings, "EMAIL_BACKEND", "")


def _send_otp_email(email, code, purpose) -> bool:
    subject = "Your verification code"
    if purpose == EmailOTP.PURPOSE_LOGIN:
        subject = "Your login verification code"
    elif purpose == EmailOTP.PURPOSE_SIGNUP:
        subject = "Verify your email (OTP)"

    if _otp_uses_console():
        print(f"\n{'='*50}\n[OTP] {email} -> {code}\n{'='*50}\n")

    context = {
        "otp": code,
        "email": email,
        "purpose": purpose,
        "expires_minutes": OTP_TTL_MINUTES,
        "app_name": "Job Portal",
    }

    text_body = render_to_string("accounts/emails/otp.txt", context)
    html_body = render_to_string("accounts/emails/otp.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        print(f"[OTP] Email delivery failed ({exc}). Code still valid: {code}")
        return False


def _stash_otp_for_display(request, code: str):
    """Fallback: show OTP on screen only when email could not be delivered."""
    request.session["pending_otp_display"] = code


def _clear_otp_display(request):
    request.session.pop("pending_otp_display", None)


def _create_and_send_otp(user, purpose, request=None) -> dict:
    """
    Send OTP email to user.email. Always returns a dict (never a tuple).
    Keys: success, wait, rate_limited, email_sent, display_on_screen
    """
    now = timezone.now()

    normalized = _normalize_email(user.email)
    if normalized and normalized != user.email:
        user.email = normalized
        user.save(update_fields=["email"])

    last = (
        EmailOTP.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if last and (now - last.created_at).total_seconds() < OTP_MIN_RESEND_SECONDS:
        wait = int(OTP_MIN_RESEND_SECONDS - (now - last.created_at).total_seconds())
        return {
            "success": True,
            "wait": wait,
            "rate_limited": True,
            "email_sent": True,
            "display_on_screen": False,
        }

    code = _generate_otp_code()
    EmailOTP.objects.create(
        user=user,
        email=user.email,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
    )
    sent = _send_otp_email(user.email, code, purpose)
    display_on_screen = False
    if request is not None:
        _clear_otp_display(request)
        if not sent or _otp_uses_console():
            _stash_otp_for_display(request, code)
            display_on_screen = True

    return {
        "success": True,
        "wait": 0,
        "rate_limited": False,
        "email_sent": sent and not _otp_uses_console(),
        "display_on_screen": display_on_screen,
    }


def _set_otp_session(request, user, purpose, user_type):
    request.session["pending_otp_user_id"] = user.id
    request.session["pending_otp_purpose"] = purpose
    request.session["pending_otp_user_type"] = user_type


def _otp_result_messages(request, user, result) -> None:
    if result.get("rate_limited"):
        messages.info(
            request,
            f"OTP was already sent to {user.email}. Wait {result['wait']}s to resend, or check inbox/spam.",
        )
    elif result.get("display_on_screen"):
        messages.warning(
            request,
            f"Could not deliver email to {user.email}. Use the code shown on the next page.",
        )
    else:
        messages.success(
            request,
            f"OTP sent to {user.email}. Please check your inbox and spam folder.",
        )

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type', 'job_seeker')

        try:
            user = CustomUser.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email)
            )
            if user_type == 'job_seeker' and not user.is_job_seeker:
                messages.error(request, "Please select the correct user type (Job Seeker).")
                return render(request, 'accounts/login.html')
            elif user_type == 'employer' and not user.is_employer:
                messages.error(request, "Please select the correct user type (Employer).")
                return render(request, 'accounts/login.html')

            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                if not user.email:
                    messages.error(request, "Your account has no email address. Please contact support.")
                    return render(request, 'accounts/login.html')

                try:
                    result = _create_and_send_otp(user, EmailOTP.PURPOSE_LOGIN, request=request)
                except Exception as e:
                    messages.error(request, f"Could not send OTP email: {e}")
                    return render(request, 'accounts/login.html')
                if not result.get("success"):
                    messages.error(request, f"Please wait {result.get('wait', 60)}s before requesting another OTP.")
                    return render(request, 'accounts/login.html')

                _set_otp_session(request, user, EmailOTP.PURPOSE_LOGIN, user_type)
                _otp_result_messages(request, user, result)
                return redirect("accounts:otp_verify")
            else:
                messages.error(request, "Invalid password.")
        except CustomUser.DoesNotExist:
            messages.error(request, "No account found with these credentials.")
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def profile_view(request):
    if request.user.is_employer:
        return redirect('dashboard:employer_dashboard')
    elif request.user.is_job_seeker:
        return redirect('dashboard:jobseeker_dashboard')
    return redirect('jobs:home')

def employer_signup(request):
    if request.method == 'POST':
        form = EmployerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            if not user.email:
                messages.error(request, "Email is required for OTP verification.")
                user.delete()
                return render(request, 'accounts/signup_employer.html', {'form': form})

            user.is_active = False
            user.save(update_fields=["is_active"])

            try:
                result = _create_and_send_otp(user, EmailOTP.PURPOSE_SIGNUP, request=request)
            except Exception as e:
                messages.error(request, f"Could not send OTP email: {e}")
                return render(request, 'accounts/signup_employer.html', {'form': form})
            if not result.get("success"):
                messages.error(request, f"Please wait {result.get('wait', 60)}s before requesting another OTP.")
                return render(request, 'accounts/signup_employer.html', {'form': form})

            _set_otp_session(request, user, EmailOTP.PURPOSE_SIGNUP, "employer")
            _otp_result_messages(request, user, result)
            return redirect("accounts:otp_verify")
    else:
        form = EmployerSignUpForm()
    return render(request, 'accounts/signup_employer.html', {'form': form})

def jobseeker_signup(request):
    if request.method == 'POST':
        form = JobSeekerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            if not user.email:
                messages.error(request, "Email is required for OTP verification.")
                user.delete()
                return render(request, 'accounts/signup_jobseeker.html', {'form': form})

            user.is_active = False
            user.save(update_fields=["is_active"])

            try:
                result = _create_and_send_otp(user, EmailOTP.PURPOSE_SIGNUP, request=request)
            except Exception as e:
                messages.error(request, f"Could not send OTP email: {e}")
                return render(request, 'accounts/signup_jobseeker.html', {'form': form})
            if not result.get("success"):
                messages.error(request, f"Please wait {result.get('wait', 60)}s before requesting another OTP.")
                return render(request, 'accounts/signup_jobseeker.html', {'form': form})

            _set_otp_session(request, user, EmailOTP.PURPOSE_SIGNUP, "job_seeker")
            _otp_result_messages(request, user, result)
            return redirect("accounts:otp_verify")
    else:
        form = JobSeekerSignUpForm()
    return render(request, 'accounts/signup_jobseeker.html', {'form': form})

def signup_view(request):
    return render(request, 'accounts/signup_choice.html')


@ensure_csrf_cookie
def otp_verify(request):
    pending_user_id = request.session.get("pending_otp_user_id")
    purpose = request.session.get("pending_otp_purpose")
    user_type = request.session.get("pending_otp_user_type")

    if not pending_user_id or purpose not in (EmailOTP.PURPOSE_SIGNUP, EmailOTP.PURPOSE_LOGIN):
        messages.error(request, "No OTP verification is pending.")
        return redirect("accounts:login")

    user = get_object_or_404(CustomUser, id=pending_user_id)
    dev_otp = request.session.get("pending_otp_display")

    def _otp_ctx(extra=None):
        ctx = {"email": user.email, "purpose": purpose, "dev_otp": dev_otp}
        if extra:
            ctx.update(extra)
        return ctx

    if request.method == "POST":
        code = (request.POST.get("otp") or "").strip()
        if not code.isdigit() or len(code) != 6:
            messages.error(request, "Please enter a valid 6-digit OTP.")
            return render(request, "accounts/otp_verify.html", _otp_ctx())

        otp = (
            EmailOTP.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not otp:
            messages.error(request, "OTP not found. Please request a new code.")
            return render(request, "accounts/otp_verify.html", _otp_ctx())

        if otp.is_expired:
            messages.error(request, "OTP expired. Please request a new code.")
            return render(request, "accounts/otp_verify.html", _otp_ctx())

        if otp.attempts >= OTP_MAX_ATTEMPTS:
            messages.error(request, "Too many attempts. Please request a new OTP.")
            return render(request, "accounts/otp_verify.html", _otp_ctx())

        if not check_password(code, otp.code_hash):
            otp.attempts = otp.attempts + 1
            otp.save(update_fields=["attempts"])
            messages.error(request, "Invalid OTP.")
            return render(request, "accounts/otp_verify.html", _otp_ctx())

        otp.consumed_at = timezone.now()
        otp.save(update_fields=["consumed_at"])

        if purpose == EmailOTP.PURPOSE_SIGNUP and not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        login(request, user)
        request.session.pop("pending_otp_user_id", None)
        request.session.pop("pending_otp_purpose", None)
        request.session.pop("pending_otp_user_type", None)
        request.session.pop("pending_otp_display", None)

        messages.success(request, "Verification successful.")
        if user.is_employer or user_type == "employer":
            return redirect("dashboard:employer_dashboard")
        return redirect("dashboard:jobseeker_dashboard")

    return render(request, "accounts/otp_verify.html", _otp_ctx())


@ensure_csrf_cookie
def otp_resend(request):
    pending_user_id = request.session.get("pending_otp_user_id")
    purpose = request.session.get("pending_otp_purpose")
    if not pending_user_id or purpose not in (EmailOTP.PURPOSE_SIGNUP, EmailOTP.PURPOSE_LOGIN):
        messages.error(request, "No OTP verification is pending.")
        return redirect("accounts:login")

    user = get_object_or_404(CustomUser, id=pending_user_id)
    try:
        result = _create_and_send_otp(user, purpose, request=request)
    except Exception as e:
        messages.error(request, f"Could not resend OTP: {e}")
        return redirect("accounts:otp_verify")
    if not result.get("success"):
        messages.error(request, f"Please wait {result.get('wait', 60)}s before requesting another OTP.")
        return redirect("accounts:otp_verify")

    _otp_result_messages(request, user, result)
    return redirect("accounts:otp_verify")

@login_required
def user_profile(request):
    if not request.user.is_job_seeker:
        messages.error(request, "Access denied. Job seeker account required.")
        return redirect('jobs:home')
    
    seeker = request.user.jobseeker
    sync_seeker_skills(seeker)
    all_active_jobs = list(Job.objects.filter(is_active=True))
    recommended_jobs = get_job_recommendations(seeker, all_active_jobs, min_score=40)[:5]

    last_analysis = request.session.get("resume_analysis")

    context = {
        'user': request.user,
        'jobseeker': seeker,
        'applications': Application.objects.filter(job_seeker=seeker),
        'recommended_jobs': recommended_jobs,
        'last_analysis': last_analysis,
    }
    return render(request, 'accounts/user_profile.html', context)


def _job_seeker_required(view_func):
    """Redirect non–job seekers away from resume tools."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_job_seeker:
            messages.error(request, "Resume analyzer is for job seeker accounts only.")
            return redirect("jobs:home")
        return view_func(request, *args, **kwargs)
    return wrapper


@_job_seeker_required
def resume_analyzer(request):
    seeker = request.user.jobseeker
    analysis_data = request.session.get("resume_analysis")
    initial = {
        "skills": seeker.skills,
        "experience": seeker.experience,
        "education": seeker.education,
        "resume_draft": request.session.get("resume_draft") or build_improved_draft(seeker),
    }
    form = ResumeAnalyzerForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == "POST":
        action = request.POST.get("action", "analyze")

        if action == "analyze" and form.is_valid():
            uploaded = request.FILES.get("resume_file") or form.cleaned_data.get("resume_file")
            seeker.skills = form.cleaned_data.get("skills") or seeker.skills
            seeker.experience = form.cleaned_data.get("experience") or seeker.experience
            seeker.education = form.cleaned_data.get("education") or seeker.education

            text = build_resume_text(seeker, uploaded)
            if not text.strip():
                messages.error(
                    request,
                    "Add skills, experience, or upload a PDF/TXT resume before analyzing.",
                )
            else:
                sync_seeker_skills(seeker, save=True)
                result = analyze_resume(text, seeker)
                analysis_data = analysis_to_dict(result)
                all_jobs = list(Job.objects.filter(is_active=True))
                analysis_data["ats"] = ats_compatibility_score(seeker, all_jobs)
                analysis_data["extracted_skills"] = seeker.extracted_skills or []
                analysis_data["missing_market_skills"] = market_missing_skills(seeker, all_jobs)
                top_recs = get_job_recommendations(seeker, all_jobs, min_score=50)
                if top_recs:
                    gap = skill_gap_for_job(seeker, top_recs[0]["job"])
                    analysis_data["skill_gap"] = {
                        "job_title": gap.job_title,
                        "job_id": gap.job_id,
                        "match_percent": gap.match_percent,
                        "required_skills": gap.required_skills,
                        "user_skills": gap.user_skills,
                        "missing_skills": gap.missing_skills,
                        "course_suggestions": gap.course_suggestions,
                    }
                draft = form.cleaned_data.get("resume_draft") or build_improved_draft(seeker, result)
                request.session["resume_analysis"] = analysis_data
                request.session["resume_draft"] = draft
                form = ResumeAnalyzerForm(
                    initial={
                        "skills": seeker.skills,
                        "experience": seeker.experience,
                        "education": seeker.education,
                        "resume_draft": draft,
                    }
                )
                messages.success(
                    request,
                    f"Analysis complete — score {result.score}/100 ({result.grade}).",
                )

        elif action == "update" and form.is_valid():
            seeker.skills = form.cleaned_data.get("skills", "")
            seeker.experience = form.cleaned_data.get("experience", "")
            seeker.education = form.cleaned_data.get("education", "")
            draft = form.cleaned_data.get("resume_draft", "")
            if draft.strip():
                filename = f"{request.user.username}_resume.txt"
                seeker.resume.save(filename, ContentFile(draft.encode("utf-8")), save=False)
            seeker.save()
            sync_seeker_skills(seeker, save=True)
            request.session["resume_draft"] = draft
            messages.success(request, "Resume and profile updated successfully.")
            return redirect("accounts:user_profile")

    context = {
        "form": form,
        "jobseeker": seeker,
        "analysis": analysis_data,
        "has_resume_file": bool(seeker.resume),
    }
    return render(request, "accounts/resume_analyzer.html", context)


def _resolve_seeker_for_resume(request, user_id=None):
    """Job seeker views own resume; employers view applicants they received."""
    if user_id is None:
        if not request.user.is_job_seeker:
            return None
        return request.user.jobseeker

    if not request.user.is_employer:
        return None

    seeker = get_object_or_404(JobSeeker, user_id=user_id)
    has_access = Application.objects.filter(
        job_seeker=seeker,
        job__employer=request.user.employer,
    ).exists()
    if not has_access:
        return None
    return seeker


def _resume_basename(seeker):
    return (seeker.resume.name or "").split("/")[-1]


def _read_resume_text(seeker) -> str:
    try:
        with seeker.resume.open("rb") as f:
            raw = f.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw)
    except (OSError, ValueError):
        return ""


@login_required
def resume_view(request, user_id=None):
    """Display resume in the browser (PDF embed or formatted text)."""
    seeker = _resolve_seeker_for_resume(request, user_id)
    if seeker is None:
        messages.error(request, "You do not have permission to view this resume.")
        return redirect("jobs:home")

    if not seeker.resume or not seeker.resume.name:
        messages.error(request, "No resume uploaded yet.")
        if request.user.is_job_seeker and user_id is None:
            return redirect("accounts:resume_analyzer")
        return redirect("jobs:home")

    basename = _resume_basename(seeker)
    lower_name = basename.lower()
    back_url = "accounts:user_profile" if user_id is None else "dashboard:employer_dashboard"

    if lower_name.endswith(".pdf"):
        file_url = (
            reverse("accounts:resume_file_seeker", kwargs={"user_id": seeker.user_id})
            if user_id
            else reverse("accounts:resume_file")
        )
        return render(
            request,
            "accounts/resume_view.html",
            {
                "seeker": seeker,
                "file_type": "pdf",
                "file_url": file_url,
                "filename": basename,
                "back_url_name": back_url,
            },
        )

    return render(
        request,
        "accounts/resume_view.html",
        {
            "seeker": seeker,
            "file_type": "text",
            "content": _read_resume_text(seeker),
            "filename": basename,
            "back_url_name": back_url,
        },
    )


@xframe_options_exempt
@login_required
def resume_file(request, user_id=None):
    """Serve resume file inline so PDFs open in the browser."""
    seeker = _resolve_seeker_for_resume(request, user_id)
    if seeker is None or not seeker.resume or not seeker.resume.name:
        return HttpResponse(status=404)

    basename = _resume_basename(seeker)
    lower_name = basename.lower()
    if lower_name.endswith(".pdf"):
        content_type = "application/pdf"
    elif lower_name.endswith(".txt"):
        content_type = "text/plain; charset=utf-8"
    else:
        content_type = "application/octet-stream"

    try:
        response = FileResponse(
            seeker.resume.open("rb"),
            content_type=content_type,
            as_attachment=False,
            filename=basename,
        )
        response["Content-Disposition"] = f'inline; filename="{basename}"'
        return response
    except (OSError, ValueError):
        return HttpResponse(status=404)


@_job_seeker_required
def job_recommendations(request):
    seeker = request.user.jobseeker
    sync_seeker_skills(seeker)
    all_jobs = list(Job.objects.filter(is_active=True).select_related("employer", "category"))
    from django.conf import settings
    min_score = float(request.GET.get("min", getattr(settings, "AI_DISPLAY_MIN_SCORE", 10)))
    recommendations = get_job_recommendations(seeker, all_jobs, min_score=min_score)
    companies = get_company_recommendations(seeker, all_jobs, min_score=min_score)
    skills = get_seeker_skills(seeker)
    gaps = []
    for rec in recommendations[:5]:
        g = skill_gap_for_job(seeker, rec["job"])
        gaps.append({"rec": rec, "gap": g})
    return render(
        request,
        "accounts/job_recommendations.html",
        {
            "recommendations": recommendations,
            "companies": companies,
            "skill_gaps": gaps,
            "extracted_skills": skills,
            "min_score": min_score,
            "inactive_days": inactive_days(request.user),
        },
    )


@_job_seeker_required
def ai_notifications(request):
    seeker = request.user.jobseeker
    if request.method == "POST":
        enabled = request.POST.get("ai_notifications_enabled") == "on"
        seeker.ai_notifications_enabled = enabled
        seeker.save(update_fields=["ai_notifications_enabled"])
        messages.success(request, "Notification preferences saved.")
        return redirect("accounts:ai_notifications")

    notifs = UserNotification.objects.filter(user=request.user)[:50]
    unread = UserNotification.objects.filter(user=request.user, is_read=False).count()
    days = inactive_days(request.user)

    if request.GET.get("mark_read") == "all":
        UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect("accounts:ai_notifications")

    return render(
        request,
        "accounts/ai_notifications.html",
        {
            "notifications": notifs,
            "unread_count": unread,
            "inactive_days": days,
            "email_enabled": seeker.ai_notifications_enabled,
            "job_alerts": notifs.filter(notification_type=UserNotification.TYPE_JOB_MATCH)[:20],
            "inactive_alerts": notifs.filter(notification_type=UserNotification.TYPE_INACTIVE)[:10],
        },
    )


@_job_seeker_required
def skill_gap_view(request, job_id):
    seeker = request.user.jobseeker
    job = get_object_or_404(Job, id=job_id, is_active=True)
    sync_seeker_skills(seeker)
    gap = skill_gap_for_job(seeker, job)
    return render(request, "accounts/skill_gap.html", {"gap": gap, "job": job})


@login_required
@require_POST
def career_chat_api(request):
    try:
        data = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        data = {}
    message = data.get("message", request.POST.get("message", ""))
    result = get_career_chat_reply(message, request.user)
    return JsonResponse(result)


@_job_seeker_required
def resume_download(request):
    seeker = request.user.jobseeker
    kind = request.GET.get("type", "improved")

    if kind == "original" and seeker.resume:
        try:
            return FileResponse(seeker.resume.open("rb"), as_attachment=True, filename=seeker.resume.name.split("/")[-1])
        except (OSError, ValueError):
            messages.error(request, "Could not open your uploaded resume.")
            return redirect("accounts:resume_analyzer")

    draft = request.session.get("resume_draft") or build_improved_draft(seeker)
    if not draft.strip():
        draft = build_resume_text(seeker)
    filename = f"{request.user.username}_resume.txt"
    response = HttpResponse(draft, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

@login_required
def employer_profile(request):
    if not request.user.is_employer:
        messages.error(request, "Access denied. Employer account required.")
        return redirect('jobs:home')
    
    total_applications = Application.objects.filter(job__employer=request.user.employer).count()

    context = {
        'user': request.user,
        'employer': request.user.employer,
        'jobs': request.user.employer.jobs.all(),
        'total_applications': total_applications,
    }
    return render(request, 'accounts/employer_profile.html', context)


@login_required
def edit_account_details(request):
    if request.user.is_job_seeker:
        profile = request.user.jobseeker
        if request.method == "POST":
            form = JobSeekerUpdateForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                sync_seeker_skills(profile, save=True)
                messages.success(request, "Your account details were updated.")
                return redirect("accounts:user_profile")
        else:
            form = JobSeekerUpdateForm(instance=profile)
        return render(
            request,
            "accounts/edit_account_details.html",
            {"form": form, "account_type": "job_seeker"},
        )

    if request.user.is_employer:
        profile = request.user.employer
        if request.method == "POST":
            form = EmployerUpdateForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Your company details were updated.")
                return redirect("accounts:employer_profile")
        else:
            form = EmployerUpdateForm(instance=profile)
        return render(
            request,
            "accounts/edit_account_details.html",
            {"form": form, "account_type": "employer"},
        )

    messages.error(request, "No editable account details found.")
    return redirect("jobs:home")