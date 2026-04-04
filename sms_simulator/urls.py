from django.urls import path
from . import views

app_name = 'sms_simulator'

urlpatterns = [
    path('', views.sms_dashboard, name='dashboard'),
    path('logs/', views.sms_logs, name='logs'),
    path('send/', views.send_sms_form, name='send'),
    path('webhook/', views.sms_webhook, name='webhook'),
]