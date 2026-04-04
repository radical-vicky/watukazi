from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:pk>/', views.notification_detail, name='detail'),
    path('<int:pk>/read/', views.notification_mark_read, name='mark_read'),
    path('<int:pk>/delete/', views.notification_delete, name='delete'),
    path('mark-all-read/', views.notification_mark_all_read, name='mark_all_read'),
    path('unread-count/', views.notification_unread_count, name='unread_count'),
]