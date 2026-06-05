"""
AI engine: skill extraction, job matching (TF-IDF + cosine), skill gaps, recommendations.
Uses scikit-learn (no heavy transformer deps required).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from django.conf import settings

# Canonical skill aliases -> display name
SKILL_TAXONOMY: dict[str, str] = {
    "python": "Python",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "reactjs": "React",
    "vue": "Vue",
    "angular": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "git": "Git",
    "github": "GitHub",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "rest": "REST API",
    "rest api": "REST API",
    "api": "REST API",
    "graphql": "GraphQL",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "nlp": "NLP",
    "data science": "Data Science",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "html": "HTML",
    "css": "CSS",
    "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "linux": "Linux",
    "agile": "Agile",
    "scrum": "Scrum",
    "excel": "Excel",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    ".net": ".NET",
    "c++": "C++",
    "c#": "C#",
    "php": "PHP",
    "laravel": "Laravel",
    "ruby": "Ruby",
    "rails": "Ruby on Rails",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "android": "Android",
    "ios": "iOS",
    "selenium": "Selenium",
    "jest": "Jest",
    "pytest": "pytest",
    "jira": "Jira",
    "figma": "Figma",
    "seo": "SEO",
    "digital marketing": "Digital Marketing",
}

COURSE_HINTS: dict[str, str] = {
    "Docker": "https://www.docker.com/101-tutorial/",
    "Kubernetes": "https://kubernetes.io/docs/tutorials/",
    "AWS": "https://aws.amazon.com/training/",
    "Git": "https://learngitbranching.js.org/",
    "REST API": "https://restfulapi.net/",
    "Machine Learning": "https://developers.google.com/machine-learning/crash-course",
    "React": "https://react.dev/learn",
    "Django": "https://docs.djangoproject.com/en/stable/intro/",
    "Python": "https://docs.python.org/3/tutorial/",
}


@dataclass
class SkillGapResult:
    job_title: str
    job_id: int
    required_skills: list[str]
    user_skills: list[str]
    missing_skills: list[str]
    match_percent: float
    course_suggestions: list[dict] = field(default_factory=list)


def extract_skills_from_text(text: str) -> list[str]:
    """Extract normalized tech skills from text (taxonomy only — no resume headers)."""
    if not text:
        return []
    lower = text.lower()
    found: set[str] = set()

    for alias, display in sorted(SKILL_TAXONOMY.items(), key=lambda x: -len(x[0])):
        pattern = r"\b" + re.escape(alias).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, lower):
            found.add(display)

    return sorted(found)


def parse_skills_field(skills_text: str) -> list[str]:
    """Parse the profile skills textarea (comma/newline separated)."""
    if not skills_text:
        return []
    found: set[str] = set()
    for token in re.split(r"[,;\n|•·]+", skills_text):
        t = token.strip()
        if not t or len(t) > 50:
            continue
        key = t.lower()
        if key in SKILL_TAXONOMY:
            found.add(SKILL_TAXONOMY[key])
        else:
            for word in t.split():
                wk = word.strip().lower()
                if wk in SKILL_TAXONOMY:
                    found.add(SKILL_TAXONOMY[wk])
    return sorted(found)


def get_seeker_skills(seeker) -> list[str]:
    """Merged skills: profile field + resume + cached."""
    found: set[str] = set()
    found.update(parse_skills_field(seeker.skills or ""))
    found.update(extract_skills_from_text(seeker_profile_text(seeker)))
    if seeker.extracted_skills:
        for s in seeker.extracted_skills:
            if s in SKILL_TAXONOMY.values():
                found.add(s)
    return sorted(found)


def skill_match_percent(user_skills: list[str], job) -> float:
    """How well user skills overlap this job (0–100)."""
    if not user_skills:
        return 0.0
    blob = job_text(job).lower()
    job_req = extract_job_required_skills(job)
    user_lower = {s.lower() for s in user_skills}

    in_description = sum(1 for s in user_skills if s.lower() in blob)
    desc_pct = (in_description / len(user_skills)) * 100

    if job_req:
        req_pct = (
            sum(1 for s in job_req if s.lower() in user_lower) / len(job_req)
        ) * 100
        return round(max(desc_pct, req_pct), 1)
    return round(desc_pct, 1)


def combined_match_score(seeker, job) -> float:
    """TF-IDF + skill overlap — best for showing companies to apply."""
    profile = seeker_profile_text(seeker)
    tfidf = similarity_score(profile, job_text(job))
    skills = get_seeker_skills(seeker)
    skill_pct = skill_match_percent(skills, job)
    return round(max(tfidf, skill_pct), 1)


def seeker_profile_text(seeker) -> str:
    from .resume_analyzer import build_resume_text

    return build_resume_text(seeker)


def job_text(job) -> str:
    return f"{job.title} {job.description} {job.requirements} {job.location}"


def similarity_score(profile_text: str, target_text: str) -> float:
    """Return match percentage 0–100."""
    if not profile_text.strip() or not target_text.strip():
        return 0.0
    try:
        tfidf = TfidfVectorizer(stop_words="english")
        matrix = tfidf.fit_transform([profile_text, target_text])
        sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return round(float(sim) * 100, 1)
    except Exception:
        return 0.0


def get_job_recommendations(seeker, all_jobs, min_score: float | None = None) -> list[dict]:
    """Rank jobs by combined TF-IDF + skill overlap."""
    if min_score is None:
        min_score = float(getattr(settings, "AI_DISPLAY_MIN_SCORE", 10))

    skills = get_seeker_skills(seeker)
    profile = seeker_profile_text(seeker)
    if not all_jobs or (not profile.strip() and not skills):
        return []

    results = []
    for job in all_jobs:
        score = combined_match_score(seeker, job)
        if score >= min_score:
            matched = [s for s in skills if s.lower() in job_text(job).lower()]
            results.append({
                "job": job,
                "score": score,
                "matched_skills": matched,
                "skill_match": skill_match_percent(skills, job),
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def get_company_recommendations(seeker, all_jobs, min_score: float | None = None) -> list[dict]:
    """Group matching jobs by company — companies to apply based on your skills."""
    recs = get_job_recommendations(seeker, all_jobs, min_score=min_score)
    skills = get_seeker_skills(seeker)
    by_employer: dict[int, dict] = {}

    for rec in recs:
        emp = rec["job"].employer
        entry = by_employer.get(emp.id)
        if not entry:
            by_employer[emp.id] = {
                "employer": emp,
                "score": rec["score"],
                "best_job": rec["job"],
                "jobs": [rec],
                "matched_skills": list(rec.get("matched_skills") or []),
            }
        else:
            entry["jobs"].append(rec)
            if rec["score"] > entry["score"]:
                entry["score"] = rec["score"]
                entry["best_job"] = rec["job"]
            for s in rec.get("matched_skills") or []:
                if s not in entry["matched_skills"]:
                    entry["matched_skills"].append(s)

    companies = sorted(by_employer.values(), key=lambda x: x["score"], reverse=True)
    for c in companies:
        if not c["matched_skills"] and skills:
            blob = " ".join(job_text(j["job"]) for j in c["jobs"]).lower()
            c["matched_skills"] = [s for s in skills if s.lower() in blob]
    return companies


def sync_seeker_skills(seeker, save: bool = True) -> list[str]:
    """Extract skills from profile + resume and cache on JobSeeker."""
    skills = get_seeker_skills(seeker)
    seeker.extracted_skills = skills
    if save:
        seeker.save(update_fields=["extracted_skills"])
    return skills


def extract_job_required_skills(job) -> list[str]:
    return extract_skills_from_text(job_text(job))


def skill_gap_for_job(seeker, job) -> SkillGapResult:
    user_skills = get_seeker_skills(seeker) or sync_seeker_skills(seeker)
    required = extract_job_required_skills(job)
    user_set = {s.lower() for s in user_skills}
    missing = [s for s in required if s.lower() not in user_set]
    match_pct = combined_match_score(seeker, job)
    courses = [
        {"skill": s, "url": COURSE_HINTS.get(s, "https://www.coursera.org/search?query=" + s.replace(" ", "%20"))}
        for s in missing[:8]
    ]
    return SkillGapResult(
        job_title=job.title,
        job_id=job.id,
        required_skills=required,
        user_skills=user_skills,
        missing_skills=missing,
        match_percent=match_pct,
        course_suggestions=courses,
    )


def market_missing_skills(seeker, all_jobs, limit: int = 10) -> list[str]:
    """Skills frequently required in jobs but missing from user profile."""
    user_set = {s.lower() for s in (get_seeker_skills(seeker) or sync_seeker_skills(seeker))}
    counts: dict[str, int] = {}
    for job in all_jobs:
        for skill in extract_job_required_skills(job):
            if skill.lower() not in user_set:
                counts[skill] = counts.get(skill, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    return [s for s, _ in ranked[:limit]]


def ats_compatibility_score(seeker, all_jobs) -> dict:
    """ATS-style score based on structure + skill coverage vs market."""
    from .resume_analyzer import analyze_resume, build_resume_text

    text = build_resume_text(seeker)
    analysis = analyze_resume(text, seeker)
    missing_market = market_missing_skills(seeker, all_jobs, limit=8)
    skill_coverage = 100
    if missing_market:
        skill_coverage = max(40, 100 - len(missing_market) * 7)
    ats = round((analysis.score * 0.6) + (skill_coverage * 0.4))
    return {
        "ats_score": min(100, ats),
        "resume_score": analysis.score,
        "missing_market_skills": missing_market,
        "grade": analysis.grade,
    }
