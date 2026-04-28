from django.urls import path
from . import views

app_name = 'employers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('update-company/', views.update_company_info, name='update_company'),
    
    # Profile views
    path('profile/', views.employer_profile_view, name='profile'),
    path('profile/<str:username>/', views.employer_public_profile, name='public_profile'),
]