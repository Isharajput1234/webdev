from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/post/', views.post_job, name='post_job'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('categories/', views.categories, name='categories'),
    path('companies/', views.companies, name='companies'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('employer/job/<int:job_id>/applicant/<int:seeker_id>/',views.view_applicant_details,name='view_applicant_details'),
    path('employer/job/<int:job_id>/applications/', views.employer_job_applications, name='employer_job_applications'),
    path('upload-jobs/', views.upload_jobs, name='upload_jobs'),
]