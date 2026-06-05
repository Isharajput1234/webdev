from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import Job, Application, Category
from .forms import JobForm, JobApplicationForm, JobSearchForm
from apps.accounts.models import Employer
import openpyxl


def _filter_jobs_by_company_industry(queryset, request):
    company_id = request.GET.get('company')
    if company_id:
        try:
            queryset = queryset.filter(employer_id=int(company_id))
        except (ValueError, TypeError):
            pass
    industry = (request.GET.get('industry') or '').strip()
    if industry:
        queryset = queryset.filter(employer__industry__iexact=industry)
    return queryset


@login_required
def employer_job_applications(request, job_id):
    # Check if logged in user is employer
    if not request.user.is_employer:
        messages.error(request, "Access denied.")
        return redirect('jobs:home')

    # Get employer object
    employer = request.user.employer

    # Ensure employer owns this job
    job = get_object_or_404(Job, id=job_id, employer=employer)

    # Get applications using related_name
    applications = job.applications.all()

    context = {
        'job': job,
        'applications': applications,
    }

    return render(request, 'jobs/employer_job_applications.html', context)

def companies(request):
    companies = Employer.objects.all()
    return render(request, 'jobs/companies.html', {'companies': companies})

def home(request):
    featured_jobs = (
        Job.objects.filter(is_active=True)
        .select_related('employer', 'category')[:6]
    )
    categories = (
        Category.objects.annotate(
            job_count=Count('job', filter=Q(job__is_active=True))
        ).order_by('name')
    )
    active_jobs_count = Job.objects.filter(is_active=True).count()
    employers_count = Employer.objects.count()
    categories_count = categories.count()

    industry_rows = (
        Job.objects.filter(is_active=True)
        .exclude(Q(employer__industry__isnull=True) | Q(employer__industry__exact=''))
        .values('employer__industry')
        .annotate(job_count=Count('id'))
        .order_by('-job_count', 'employer__industry')[:24]
    )
    industry_browse = [
        {'name': row['employer__industry'], 'job_count': row['job_count']}
        for row in industry_rows
    ]
    context = {
        'featured_jobs': featured_jobs,
        'categories': categories,
        'industry_browse': industry_browse,
        'active_jobs_count': active_jobs_count,
        'employers_count': employers_count,
        'categories_count': categories_count,
    }
    return render(request, 'jobs/home.html', context)

def job_list(request):
    form = JobSearchForm(request.GET or None)
    jobs = Job.objects.filter(is_active=True).select_related('employer')
    jobs = _filter_jobs_by_company_industry(jobs, request)

    if form.is_valid():
        search = form.cleaned_data.get('search')
        location = form.cleaned_data.get('location')
        category = form.cleaned_data.get('category')
        job_type = form.cleaned_data.get('job_type')

        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        if location:
            jobs = jobs.filter(location__icontains=location)
        if category:
            jobs = jobs.filter(category=category)
        if job_type:
            jobs = jobs.filter(job_type=job_type)

    paginator = Paginator(jobs, 9)
    page = request.GET.get('page')
    jobs = paginator.get_page(page)

    context = {
        'jobs': jobs,
        'form': form,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, job_id):
    job = get_object_or_404(
        Job.objects.select_related('employer'),
        id=job_id,
        is_active=True,
    )
    application_form = JobApplicationForm() if request.user.is_authenticated else None
    has_applied = False
    can_apply = False

    if request.user.is_authenticated and getattr(request.user, 'is_job_seeker', False) and hasattr(request.user, 'jobseeker'):
        has_applied = Application.objects.filter(
            job=job, job_seeker=request.user.jobseeker
        ).exists()
        can_apply = True

    context = {
        'job': job,
        'application_form': application_form,
        'has_applied': has_applied,
        'can_apply': can_apply,
    }
    return render(request, 'jobs/job_detail.html', context)

@login_required
def post_job(request):
    if not hasattr(request.user, 'employer'):
        return redirect('jobs:home')
        
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = request.user.employer
            job.save()
            messages.success(request, "Job posted successfully!")
            return redirect('jobs:job_detail', job_id=job.id)
    else:
        form = JobForm()

    return render(request, 'jobs/post_job.html', {'form': form})

@login_required
def apply_job(request, job_id):
    if not request.user.is_job_seeker:
        messages.error(request, "Only job seekers can apply for jobs.")
        return redirect('jobs:job_detail', job_id=job_id)

    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    if Application.objects.filter(job=job, job_seeker=request.user.jobseeker).exists():
        messages.info(request, "You have already applied for this job.")
        return redirect('jobs:job_detail', job_id=job_id)

    if request.method == 'POST':
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.job_seeker = request.user.jobseeker
            application.save()
            messages.success(request, "Application submitted successfully!")
            return redirect('dashboard:jobseeker_dashboard')

    return redirect('jobs:job_detail', job_id=job_id)

def search_jobs(request):
    form = JobSearchForm(request.GET)
    jobs = Job.objects.filter(is_active=True)
    jobs = _filter_jobs_by_company_industry(jobs, request)

    if form.is_valid():
        search = form.cleaned_data.get('search')
        location = form.cleaned_data.get('location')
        category = form.cleaned_data.get('category')
        job_type = form.cleaned_data.get('job_type')

        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        if location:
            jobs = jobs.filter(location__icontains=location)
        if category:
            jobs = jobs.filter(category=category)
        if job_type:
            jobs = jobs.filter(job_type=job_type)

    paginator = Paginator(jobs, 9)
    page = request.GET.get('page')
    jobs = paginator.get_page(page)

    context = {
        'jobs': jobs,
        'form': form,
    }
    return render(request, 'jobs/search_results.html', context)

def categories(request):
    categories_qs = (
        Category.objects.annotate(
            job_count=Count('job', filter=Q(job__is_active=True))
        ).order_by('name')
    )
    context = {'categories': categories_qs}
    return render(request, 'jobs/categories.html', context)

def company_detail(request, pk):
    company = get_object_or_404(Employer, pk=pk)
    active_jobs = Job.objects.filter(employer=company, is_active=True)
    
    context = {
        'company': company,
        'active_jobs': active_jobs,
    }
    return render(request, 'jobs/company_detail.html', context)

@login_required
def view_applicant_details(request, job_id, seeker_id):
    if not request.user.is_employer:
        messages.error(request, "Access denied.")
        return redirect('jobs:home')

    employer = request.user.employer
    job = get_object_or_404(Job, id=job_id, employer=employer)
    application = get_object_or_404(Application, job=job, job_seeker__id=seeker_id)
    job_seeker = application.job_seeker

    context = {
        'job_seeker': job_seeker,
        'application': application,
        'job': job,
    }
    return render(request, 'jobs/applicant_details.html', context)

@login_required
def upload_jobs(request):
    if not hasattr(request.user, 'employer'):
        messages.error(request, "Only employers can upload jobs.")
        return redirect('jobs:home')

    if request.method == "POST":
        file = request.FILES.get('file')
        if not file:
            messages.error(request, "No file uploaded.")
            return redirect('jobs:home')

        try:
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            employer = request.user.employer
            category = Category.objects.first()
            jobs = []

            for row in sheet.iter_rows(min_row=2, values_only=True):
                title, description, requirements, location, salary, job_type = row
                jobs.append(Job(
                    title=title, employer=employer, category=category,
                    description=description, requirements=requirements,
                    location=location, salary=salary, job_type=job_type
                ))

            Job.objects.bulk_create(jobs)
            messages.success(request, f"{len(jobs)} Jobs uploaded successfully!")
            return redirect('jobs:job_list')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('jobs:home')

    return render(request, 'jobs/upload_jobs.html')