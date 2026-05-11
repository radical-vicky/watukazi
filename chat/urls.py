from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.conversations_list, name='conversations_list'),
    path('conversation/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversation/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('conversation/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('conversation/<int:conversation_id>/mark-read/', views.mark_conversation_read, name='mark_conversation_read'),
    
    # Two patterns for starting conversations
    path('start/<int:job_id>/', views.start_conversation, name='start_conversation'),  # For workers
    path('start/<int:job_id>/<int:worker_id>/', views.start_conversation, name='start_conversation_with_worker'),  # For employers
    
    path('unread-count/', views.get_unread_count, name='unread_count'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
]