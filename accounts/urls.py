from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_page, name='home'),
    
    # Worker URLs
    path('worker/login/', views.worker_login, name='worker_login'),
    path('worker/signup/', views.worker_signup, name='worker_signup'),
    
    # Employer URLs
    path('employer/login/', views.employer_login, name='employer_login'),
    path('employer/signup/', views.employer_signup, name='employer_signup'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='account/password_reset.html',
             email_template_name='account/password_reset_email.html',
             subject_template_name='account/password_reset_subject.txt',
             success_url=reverse_lazy('accounts:password_reset_done')
         ),
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='account/password_reset_done.html'
         ),
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='account/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete')
         ),
         name='password_reset_confirm'),
    
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='account/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Logout
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='account_logout'),
]