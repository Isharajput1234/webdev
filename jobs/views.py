from django.shortcuts import render
from django.contrib import messages
from apps.jobs.models import Job

def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    
    # Handle category filter
    category_id = request.GET.get('category')
    if category_id:
        jobs = jobs.filter(category_id=category_id)
        
        # If no jobs found for category
        if not jobs.exists():
            messages.info(request, "No jobs available in this category at the moment.")
            
    return render(request, 'jobs/job_list.html', {'jobs': jobs}) 