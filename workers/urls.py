from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update-availability/', views.update_availability, name='update_availability'),
    path('add-skills/', views.add_skills, name='add_skills'),
    path('my-profile/', views.worker_profile_view, name='profile'),
    path('profile/<str:username>/', views.worker_profile_view, name='public_profile'),
    path('edit-bio/', views.edit_bio, name='edit_bio'),
    path('manage-skills/', views.manage_skills, name='manage_skills'),
    path('request-verification/', views.request_verification, name='request_verification'),
    path('verify-code/', views.verify_code, name='verify_code'),
    
    # New URLs for job confirmation and directions
    path('confirm-job/<int:match_id>/', views.confirm_job, name='confirm_job'),
    path('my-confirmations/', views.my_confirmations, name='my_confirmations'),
    path('upcoming-jobs/', views.my_upcoming_jobs, name='upcoming_jobs'),
]