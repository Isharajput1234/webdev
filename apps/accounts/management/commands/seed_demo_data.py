import re
import time
import unicodedata
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import OperationalError, transaction

from apps.accounts.models import CustomUser, Employer, JobSeeker
from apps.jobs.models import Category, Job

# ~30 well-known technology companies with every Employer field filled for realistic demos.
TECH_COMPANIES = [
    {
        "name": "Google",
        "industry": "Internet & Cloud",
        "location": "Mountain View, CA",
        "website": "https://careers.google.com",
        "description": "Search, ads, Android, Chrome, and Google Cloud — global technology company.",
    },
    {
        "name": "Microsoft",
        "industry": "Software & Cloud",
        "location": "Redmond, WA",
        "website": "https://careers.microsoft.com",
        "description": "Azure, Windows, Office 365, GitHub, and enterprise productivity platforms.",
    },
    {
        "name": "Apple",
        "industry": "Consumer Electronics",
        "location": "Cupertino, CA",
        "website": "https://jobs.apple.com",
        "description": "iPhone, Mac, iPad, wearables, and services including App Store and iCloud.",
    },
    {
        "name": "Amazon",
        "industry": "E-commerce & Cloud (AWS)",
        "location": "Seattle, WA",
        "website": "https://www.amazon.jobs",
        "description": "Retail marketplace, logistics, and Amazon Web Services cloud infrastructure.",
    },
    {
        "name": "Meta",
        "industry": "Social & VR",
        "location": "Menlo Park, CA",
        "website": "https://www.metacareers.com",
        "description": "Facebook, Instagram, WhatsApp, and Reality Labs virtual and mixed reality.",
    },
    {
        "name": "Netflix",
        "industry": "Streaming Media",
        "location": "Los Gatos, CA",
        "website": "https://jobs.netflix.com",
        "description": "Subscription streaming and global content production at scale.",
    },
    {
        "name": "Salesforce",
        "industry": "CRM & SaaS",
        "location": "San Francisco, CA",
        "website": "https://careers.salesforce.com",
        "description": "Customer relationship management, Slack, Tableau, and enterprise cloud apps.",
    },
    {
        "name": "Adobe",
        "industry": "Creative Software",
        "location": "San Jose, CA",
        "website": "https://careers.adobe.com",
        "description": "Creative Cloud, Acrobat, Experience Cloud, and digital document workflows.",
    },
    {
        "name": "Oracle",
        "industry": "Enterprise Database",
        "location": "Austin, TX",
        "website": "https://careers.oracle.com",
        "description": "Database, Fusion Cloud applications, and enterprise infrastructure software.",
    },
    {
        "name": "IBM",
        "industry": "Hybrid Cloud & AI",
        "location": "Armonk, NY",
        "website": "https://www.ibm.com/careers",
        "description": "Consulting, Red Hat OpenShift, watsonx AI, and mainframe modernization.",
    },
    {
        "name": "Intel",
        "industry": "Semiconductors",
        "location": "Santa Clara, CA",
        "website": "https://jobs.intel.com",
        "description": "CPUs, accelerators, and foundry services for data center and client computing.",
    },
    {
        "name": "Nvidia",
        "industry": "AI & Accelerated Computing",
        "location": "Santa Clara, CA",
        "website": "https://www.nvidia.com/en-us/about-nvidia/careers",
        "description": "GPUs, CUDA, AI platforms, and Omniverse simulation software.",
    },
    {
        "name": "AMD",
        "industry": "Semiconductors",
        "location": "Santa Clara, CA",
        "website": "https://careers.amd.com",
        "description": "High-performance CPUs and GPUs for PCs, servers, and gaming.",
    },
    {
        "name": "Cisco",
        "industry": "Networking",
        "location": "San Jose, CA",
        "website": "https://jobs.cisco.com",
        "description": "Routers, switches, security, collaboration, and observability for enterprises.",
    },
    {
        "name": "SAP",
        "industry": "Enterprise Software",
        "location": "Walldorf, Germany",
        "website": "https://jobs.sap.com",
        "description": "ERP, supply chain, HR, and analytics for large organizations worldwide.",
    },
    {
        "name": "ServiceNow",
        "industry": "Workflow SaaS",
        "location": "Santa Clara, CA",
        "website": "https://careers.servicenow.com",
        "description": "IT service management, employee workflows, and low-code automation.",
    },
    {
        "name": "Workday",
        "industry": "HCM & Finance Cloud",
        "location": "Pleasanton, CA",
        "website": "https://careers.workday.com",
        "description": "Human capital management, payroll, and financial planning in the cloud.",
    },
    {
        "name": "Stripe",
        "industry": "Fintech Infrastructure",
        "location": "San Francisco, CA",
        "website": "https://stripe.com/jobs",
        "description": "Online payments, billing, and financial tools for internet businesses.",
    },
    {
        "name": "Shopify",
        "industry": "E-commerce Platform",
        "location": "Ottawa, Canada",
        "website": "https://www.shopify.com/careers",
        "description": "Commerce OS for merchants: storefronts, payments, and logistics integrations.",
    },
    {
        "name": "Airbnb",
        "industry": "Marketplace",
        "location": "San Francisco, CA",
        "website": "https://careers.airbnb.com",
        "description": "Global travel and experiences marketplace with trust and safety at scale.",
    },
    {
        "name": "Uber",
        "industry": "Mobility & Delivery",
        "location": "San Francisco, CA",
        "website": "https://www.uber.com/careers",
        "description": "Ride-hailing, food delivery, and freight with real-time logistics.",
    },
    {
        "name": "Spotify",
        "industry": "Audio Streaming",
        "location": "Stockholm, Sweden",
        "website": "https://www.lifeatspotify.com",
        "description": "Music and podcast streaming with personalization and creator tools.",
    },
    {
        "name": "Dell Technologies",
        "industry": "IT Hardware & Services",
        "location": "Round Rock, TX",
        "website": "https://jobs.dell.com",
        "description": "Servers, storage, PCs, and VMware-based hybrid cloud solutions.",
    },
    {
        "name": "HP",
        "industry": "Computing & Printing",
        "location": "Palo Alto, CA",
        "website": "https://jobs.hp.com",
        "description": "Personal systems, printers, and workplace collaboration devices.",
    },
    {
        "name": "Lenovo",
        "industry": "Devices & Infrastructure",
        "location": "Morrisville, NC",
        "website": "https://jobs.lenovo.com",
        "description": "ThinkPad, servers, and solutions for enterprise and consumer markets.",
    },
    {
        "name": "Qualcomm",
        "industry": "Wireless & Mobile",
        "location": "San Diego, CA",
        "website": "https://careers.qualcomm.com",
        "description": "Snapdragon platforms, 5G modems, and IoT connectivity.",
    },
    {
        "name": "Palantir",
        "industry": "Data Analytics",
        "location": "Denver, CO",
        "website": "https://jobs.lever.co/palantir",
        "description": "Data integration and analytics platforms for government and commercial sectors.",
    },
    {
        "name": "Snowflake",
        "industry": "Data Cloud",
        "location": "Bozeman, MT",
        "website": "https://careers.snowflake.com",
        "description": "Cloud data warehouse, sharing, and AI/ML workloads on a unified platform.",
    },
    {
        "name": "Atlassian",
        "industry": "Team Collaboration",
        "location": "Sydney, Australia",
        "website": "https://www.atlassian.com/company/careers",
        "description": "Jira, Confluence, Bitbucket, and developer collaboration tools.",
    },
    {
        "name": "Datadog",
        "industry": "Observability & Security",
        "location": "New York, NY",
        "website": "https://careers.datadoghq.com",
        "description": "Monitoring, logging, APM, and cloud security for modern applications.",
    },
]

DEMO_CATEGORIES = [
    ("Software Engineering", "fas fa-code"),
    ("Data & Analytics", "fas fa-chart-line"),
    ("Product & Design", "fas fa-pen-nib"),
    ("Cloud & Infrastructure", "fas fa-cloud"),
    ("Security", "fas fa-shield-halved"),
]

DEMO_ROLES = [
    "Software Engineer",
    "Senior Backend Developer",
    "Data Scientist",
    "Product Manager",
    "DevOps Engineer",
    "UX Designer",
    "Machine Learning Engineer",
    "Site Reliability Engineer",
    "Frontend Engineer",
    "Technical Program Manager",
]

JOB_TYPES = ["full_time", "part_time", "contract", "internship"]

SEEKERS = [
    ("isha", "isha@jobportal.demo"),
    ("radhika", "radhika@jobportal.demo"),
    ("atulya", "atulya@jobportal.demo"),
    ("niharika", "niharika@jobportal.demo"),
]


def slugify_username(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "company"
    return f"co_{s}"[:140]


def ensure_categories():
    cats = []
    for name, icon in DEMO_CATEGORIES:
        obj, _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})
        cats.append(obj)
    return cats


def seed_demo_job(employer: Employer, company: dict, idx: int, categories: list[Category]) -> bool:
    """One demo job per employer; skips if a demo job for this employer already exists."""
    name = company["name"]
    demo_marker = f"Demo opening — {name}"
    if Job.objects.filter(employer=employer, title__startswith="Demo opening —").exists():
        return False

    role = DEMO_ROLES[idx % len(DEMO_ROLES)]
    job_type = JOB_TYPES[idx % len(JOB_TYPES)]
    category = categories[idx % len(categories)]
    title = f"{demo_marker}: {role}"

    salary_band = ["$120k–$160k", "$95k–$130k", "$140k–$180k", "Competitive + equity"][idx % 4]
    loc = company["location"]
    if idx % 3 == 1:
        job_location = "Remote (US)"
    elif idx % 3 == 2:
        job_location = f"{loc} / Hybrid"
    else:
        job_location = loc

    deadline = date.today() + timedelta(days=21 + (idx % 40))

    Job.objects.create(
        title=title,
        employer=employer,
        category=category,
        description=(
            f"Portfolio demo listing for {name}. {company['description']} "
            f"This role focuses on {role.lower()} work with modern tooling and CI/CD."
        ),
        requirements=(
            "3+ years relevant experience; strong communication; collaborative mindset. "
            "Demo seed data — replace with real requirements in production."
        ),
        location=job_location,
        salary=salary_band,
        job_type=job_type,
        deadline=deadline,
        is_active=True,
    )
    return True


class Command(BaseCommand):
    help = (
        "Seed ~30 tech employers (realistic fields) with one demo job each, plus demo job seekers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--employer-password",
            default="demo1234",
            help="Password for all seeded employer accounts (default: demo1234).",
        )
        parser.add_argument(
            "--seeker-password",
            default="one",
            help="Password for seeded job seeker accounts (default: one).",
        )

    def handle(self, *args, **options):
        employer_pw = options["employer_password"]
        seeker_pw = options["seeker_password"]

        created_employers = skipped_employers = created_seekers = created_jobs = 0
        seeker_warnings = []

        for attempt in range(8):
            try:
                with transaction.atomic():
                    created_employers = 0
                    skipped_employers = 0
                    created_jobs = 0
                    used_usernames = set(CustomUser.objects.values_list("username", flat=True))
                    categories = ensure_categories()

                    for idx, company in enumerate(TECH_COMPANIES):
                        if Employer.objects.filter(company_name=company["name"]).exists():
                            skipped_employers += 1
                            continue

                        base = slugify_username(company["name"])
                        username = base
                        n = 2
                        while username in used_usernames:
                            suffix = f"_{n}"
                            username = (base[: 140 - len(suffix)] + suffix)[:150]
                            n += 1
                        used_usernames.add(username)

                        user = CustomUser.objects.create_user(
                            username=username,
                            email=f"{username}@employers.jobportal.local",
                            password=employer_pw,
                            is_employer=True,
                            is_job_seeker=False,
                        )
                        employer = Employer.objects.create(
                            user=user,
                            company_name=company["name"],
                            company_description=company["description"],
                            company_website=company["website"],
                            location=company["location"],
                            industry=company["industry"],
                        )
                        created_employers += 1
                        if seed_demo_job(employer, company, idx, categories):
                            created_jobs += 1

                    created_seekers = 0
                    for username, email in SEEKERS:
                        if CustomUser.objects.filter(username=username).exists():
                            seeker_warnings.append(username)
                            continue
                        user = CustomUser.objects.create_user(
                            username=username,
                            email=email,
                            password=seeker_pw,
                            is_job_seeker=True,
                            is_employer=False,
                        )
                        JobSeeker.objects.create(
                            user=user,
                            skills="Python, teamwork, communication, problem solving.",
                            experience="Demo experience entry for portfolio / testing.",
                            education="Demo education entry.",
                        )
                        created_seekers += 1
                break
            except OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < 7:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise

        for w in seeker_warnings:
            self.stdout.write(self.style.WARNING(f"Skip seeker (exists): {w}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Employers: {created_employers} created, {skipped_employers} skipped (already present). "
                f"Demo jobs created: {created_jobs}. Tech companies in seed list: {len(TECH_COMPANIES)}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Job seekers: {created_seekers} created. Default password (unless overridden): {seeker_pw!r}"
            )
        )
        self.stdout.write(f"Employer login password (unless overridden): {employer_pw!r}")
