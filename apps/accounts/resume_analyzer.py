"""
Rule-based resume analyzer: extracts text, scores content, and returns actionable suggestions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ACTION_VERBS = {
    "achieved", "built", "created", "delivered", "designed", "developed",
    "implemented", "improved", "increased", "led", "managed", "optimized",
    "reduced", "resolved", "spearheaded", "streamlined", "launched", "coordinated",
}
SECTION_KEYWORDS = {
    "skills": ("skills", "technical skills", "core competencies", "technologies"),
    "experience": ("experience", "work experience", "employment", "professional experience"),
    "education": ("education", "academic", "qualification", "degree"),
}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")
METRIC_RE = re.compile(r"\d+\s*%|\$\d+|\d+\+?\s*(users|clients|projects|team|people|customers)", re.I)


@dataclass
class AnalysisResult:
    score: int
    grade: str
    word_count: int
    suggestions: list[dict] = field(default_factory=list)
    sections_found: dict[str, bool] = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)


def extract_text_from_file(uploaded_file) -> str:
    """Read plain text from resume file (txt or pdf)."""
    if not uploaded_file:
        return ""

    name = (getattr(uploaded_file, "name", "") or "").lower()
    uploaded_file.seek(0)

    if name.endswith(".txt"):
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw)

    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        reader = PdfReader(uploaded_file)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
        return "\n".join(pages)

    return ""


def build_resume_text(seeker, uploaded_file=None) -> str:
    """Combine profile fields and uploaded resume into one analyzable document."""
    chunks = []
    user = seeker.user
    header = []
    if user.get_full_name():
        header.append(user.get_full_name())
    if user.email:
        header.append(user.email)
    if header:
        chunks.append("\n".join(header))

    if seeker.skills:
        chunks.append(f"SKILLS\n{seeker.skills.strip()}")
    if seeker.experience:
        chunks.append(f"EXPERIENCE\n{seeker.experience.strip()}")
    if seeker.education:
        chunks.append(f"EDUCATION\n{seeker.education.strip()}")

    file_text = ""
    if uploaded_file:
        file_text = extract_text_from_file(uploaded_file)
    elif seeker.resume:
        try:
            with seeker.resume.open("rb") as f:
                file_text = extract_text_from_file(f)
        except (OSError, ValueError):
            file_text = ""

    if file_text.strip():
        chunks.append(file_text.strip())

    return "\n\n".join(chunks).strip()


def _detect_sections(text: str) -> dict[str, bool]:
    lower = text.lower()
    found = {}
    for key, keywords in SECTION_KEYWORDS.items():
        found[key] = any(kw in lower for kw in keywords)
    return found


def _grade_from_score(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    return "Needs Work"


def analyze_resume(text: str, seeker=None) -> AnalysisResult:
    """Score resume and return prioritized suggestions."""
    text = (text or "").strip()
    words = re.findall(r"\b[a-zA-Z]{2,}\b", text)
    word_count = len(words)
    lower = text.lower()

    suggestions: list[dict] = []
    highlights: list[str] = []
    score = 100

    def add(priority: str, title: str, detail: str, penalty: int = 0):
        nonlocal score
        suggestions.append({"priority": priority, "title": title, "detail": detail})
        score = max(0, score - penalty)

    sections = _detect_sections(text)

    if word_count < 80:
        add("high", "Resume is too short", "Aim for at least 150–300 words covering skills, experience, and education.", 18)
    elif word_count > 900:
        add("medium", "Resume may be too long", "Recruiters often prefer 1–2 pages. Trim older or less relevant details.", 8)
    else:
        highlights.append(f"Solid length ({word_count} words).")

    if not sections.get("skills"):
        add("high", "Add a skills section", "List 8–15 relevant skills (tools, languages, frameworks) as bullets or comma-separated.", 15)
    else:
        highlights.append("Skills section detected.")

    if not sections.get("experience"):
        add("high", "Add work experience", "Include job titles, company names, dates, and bullet points with outcomes.", 15)
    else:
        highlights.append("Experience section detected.")

    if not sections.get("education"):
        add("medium", "Add education details", "Include degree, institution, and graduation year (or expected year).", 10)

    verb_hits = sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", lower))
    if sections.get("experience") and verb_hits < 2:
        add(
            "high",
            "Use stronger action verbs",
            "Start bullets with verbs like Developed, Led, Improved, Delivered, and quantify results.",
            12,
        )
    elif verb_hits >= 3:
        highlights.append(f"Good use of action verbs ({verb_hits} found).")

    if not METRIC_RE.search(text):
        add(
            "medium",
            "Add measurable achievements",
            "Include numbers: % improvements, team size, revenue, users, or project counts.",
            10,
        )
    else:
        highlights.append("Quantified achievements found.")

    if seeker and seeker.user and not seeker.user.email and not EMAIL_RE.search(text):
        add("medium", "Add contact email", "Ensure your email appears at the top of the resume.", 8)
    elif EMAIL_RE.search(text):
        highlights.append("Email contact found.")

    if not PHONE_RE.search(text):
        add("low", "Consider adding a phone number", "A phone line helps recruiters reach you quickly.", 4)

    skill_tokens = re.split(r"[,;\n|]+", (seeker.skills if seeker else "") or text)
    skill_count = len([s for s in skill_tokens if len(s.strip()) > 2])
    if skill_count < 5 and sections.get("skills"):
        add("medium", "Expand your skills list", "Add more role-relevant skills to improve ATS matching.", 8)
    elif skill_count >= 8:
        highlights.append(f"Rich skills list ({skill_count} items).")

    if re.search(r"\bi\s+(am|was)\b", lower):
        add("low", "Reduce first-person phrasing", 'Prefer "Developed API..." instead of "I developed API...".', 5)

    if re.search(r"(objective|career objective)\s*:", lower) and word_count < 200:
        add("low", "Replace objective with a summary", "A 2–3 line professional summary is stronger than a generic objective.", 4)

    score = min(100, max(0, score))
    return AnalysisResult(
        score=score,
        grade=_grade_from_score(score),
        word_count=word_count,
        suggestions=sorted(suggestions, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s["priority"]]),
        sections_found=sections,
        highlights=highlights,
    )


def build_improved_draft(seeker, analysis: AnalysisResult | None = None) -> str:
    """Structured resume text the user can edit before saving."""
    user = seeker.user
    lines = []

    name = user.get_full_name() or user.username
    lines.append(name.upper())
    lines.append("=" * len(name))
    if user.email:
        lines.append(f"Email: {user.email}")

    lines.append("")
    lines.append("PROFESSIONAL SUMMARY")
    lines.append("-" * 20)
    summary_bits = []
    if seeker.skills:
        top_skills = ", ".join(s.strip() for s in seeker.skills.split(",")[:5] if s.strip())
        if top_skills:
            summary_bits.append(f"Professional with expertise in {top_skills}.")
    if seeker.experience:
        summary_bits.append("Experienced contributor with a track record of delivering results.")
    lines.append(
        " ".join(summary_bits)
        if summary_bits
        else "Motivated professional seeking opportunities to apply skills and grow impact."
    )

    lines.append("")
    lines.append("SKILLS")
    lines.append("-" * 6)
    lines.append(seeker.skills.strip() if seeker.skills else "• Add your key skills here")

    lines.append("")
    lines.append("EXPERIENCE")
    lines.append("-" * 10)
    if seeker.experience:
        lines.append(seeker.experience.strip())
    else:
        lines.append("• Role Title | Company | Dates")
        lines.append("  - Action verb + task + measurable result")

    lines.append("")
    lines.append("EDUCATION")
    lines.append("-" * 9)
    lines.append(seeker.education.strip() if seeker.education else "• Degree | Institution | Year")

    if analysis and analysis.suggestions:
        lines.append("")
        lines.append("TIP (from analyzer)")
        lines.append("-" * 16)
        lines.append(f"• {analysis.suggestions[0]['title']}: {analysis.suggestions[0]['detail']}")

    return "\n".join(lines)


def analysis_to_dict(result: AnalysisResult) -> dict:
    return {
        "score": result.score,
        "grade": result.grade,
        "word_count": result.word_count,
        "suggestions": result.suggestions,
        "sections_found": result.sections_found,
        "highlights": result.highlights,
    }
