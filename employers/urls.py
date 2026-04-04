from django.urls import path
from . import views

app_name = 'employers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('update-company/', views.update_company_info, name='update_company'),
]