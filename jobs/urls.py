from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Public URLs (no login required)
    path('browse/', views.public_jobs, name='public_jobs'),
    
    # Job CRUD operations
    path('create/', views.create_job, name='create_job'),
    path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('<int:job_id>/delete/', views.delete_job, name='delete_job'),
    
    # Match operations
    path('match/<int:match_id>/accept/', views.accept_match, name='accept_match'),
    path('match/<int:match_id>/reject/', views.reject_match, name='reject_match'),
    path('match/<int:match_id>/respond/', views.worker_respond_match, name='worker_respond'),
    path('match/<int:match_id>/complete/', views.complete_job, name='complete_job'),
    path('match/<int:match_id>/rate-employer/', views.rate_employer, name='rate_employer'),
    
    # Worker views
    path('my-applications/', views.my_applications, name='my_applications'),
    path('search/', views.search_jobs, name='search_jobs'),
]