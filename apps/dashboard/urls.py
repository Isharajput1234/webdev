from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('employer/', views.employer_dashboard, name='employer_dashboard'),
    path('jobseeker/', views.job_seeker_dashboard, name='jobseeker_dashboard'),
    path('application/<int:application_id>/manage/', views.manage_application, name='manage_application'),
    path('application/<int:application_id>/edit/', views.edit_application, name='edit_application'),
    path('application/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
]
