"""
AI Career Assistant — OpenAI, Gemini, or rule-based fallback.
"""
from __future__ import annotations

import json
import os
import urllib.request

from django.conf import settings

from apps.jobs.models import Job
from apps.accounts.ai_engine import (
    get_job_recommendations,
    get_company_recommendations,
    get_seeker_skills,
    seeker_profile_text,
    sync_seeker_skills,
)


def _format_companies_reply(seeker, site_url: str) -> str:
    jobs = list(Job.objects.filter(is_active=True).select_related("employer"))
    sync_seeker_skills(seeker)
    skills = get_seeker_skills(seeker)
    companies = get_company_recommendations(seeker, jobs, min_score=15)[:6]

    if not companies:
        return (
            "I couldn't find companies yet. Add skills (e.g. Python, Django, React) in "
            "Profile → Edit details, then open AI Job Matches."
        )

    lines = [f"Based on your skills ({', '.join(skills[:8]) or 'profile'}), apply at:\n"]
    for c in companies:
        emp = c["employer"]
        matched = ", ".join(c["matched_skills"][:4]) or "profile match"
        lines.append(
            f"• **{emp.company_name}** ({c['score']}% match)\n"
            f"  Role: {c['best_job'].title}\n"
            f"  Skills: {matched}\n"
            f"  Apply: {site_url}/jobs/{c['best_job'].id}/"
        )
    lines.append(f"\nSee all: {site_url}/accounts/ai/recommendations/")
    return "\n".join(lines)


def _rule_based_reply(message: str, user) -> str:
    lower = message.lower()
    site = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")

    if not user.is_authenticated:
        return "Please log in as a job seeker to get personalized career advice."

    if user.is_job_seeker and hasattr(user, "jobseeker"):
        seeker = user.jobseeker

        if any(
            k in lower
            for k in (
                "company",
                "companies",
                "apply",
                "where should",
                "who should i",
                "employer",
                "hire me",
            )
        ):
            return _format_companies_reply(seeker, site)

    if "improve" in lower and "resume" in lower:
        return (
            "To improve your resume: add a Skills section with 8–12 technologies, "
            "use action verbs (Developed, Led, Delivered), include metrics (%, $, team size), "
            "and open the Resume Analyzer from your Profile for a score and suggestions."
        )
    if "interview" in lower and "python" in lower:
        return (
            "Sample Python interview topics: data structures, OOP, decorators, "
            "Django ORM, REST APIs, testing with pytest, and system design basics."
        )
    if any(k in lower for k in ("job", "suit", "match", "recommend", "skill")):
        if user.is_job_seeker and hasattr(user, "jobseeker"):
            return _format_companies_reply(user.jobseeker, site)
        return "Sign up as a job seeker and add your skills to get personalized matches."

    return (
        "Ask me:\n"
        "• 'Which companies should I apply to?'\n"
        "• 'What jobs match my skills?'\n"
        "• 'How can I improve my resume?'\n"
        "Set OPENAI_API_KEY or GEMINI_API_KEY in .env for smarter answers."
    )


def _openai_reply(message: str, user) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    context = ""
    if user.is_authenticated and user.is_job_seeker and hasattr(user, "jobseeker"):
        seeker = user.jobseeker
        sync_seeker_skills(seeker)
        skills = get_seeker_skills(seeker)
        context = (
            f"Skills: {', '.join(skills)}. Profile: {seeker_profile_text(seeker)[:1200]}"
        )

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a career assistant for a job portal. "
                    "Recommend specific companies and jobs based on user skills. "
                    "Be concise and list companies with match %. " + context
                ),
            },
            {"role": "user", "content": message},
        ],
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _gemini_reply(message: str, user) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    context = ""
    if user.is_authenticated and user.is_job_seeker and hasattr(user, "jobseeker"):
        seeker = user.jobseeker
        sync_seeker_skills(seeker)
        context = f"Skills: {', '.join(get_seeker_skills(seeker))}"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Career assistant. Suggest companies to apply based on skills.\n"
                            f"{context}\n\nUser: {message}"
                        )
                    }
                ]
            }
        ]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def get_career_chat_reply(message: str, user) -> dict:
    message = (message or "").strip()[:2000]
    if not message:
        return {"reply": "Please enter a question.", "provider": "none"}

    provider = os.getenv("AI_CHAT_PROVIDER", "auto").lower()
    reply = None
    used = "rules"

    if provider in ("openai", "auto"):
        reply = _openai_reply(message, user)
        if reply:
            used = "openai"
    if not reply and provider in ("gemini", "auto"):
        reply = _gemini_reply(message, user)
        if reply:
            used = "gemini"
    if not reply:
        reply = _rule_based_reply(message, user)
        used = "rules"

    return {"reply": reply, "provider": used}
