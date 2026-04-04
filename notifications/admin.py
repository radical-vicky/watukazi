from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('created_at', 'read_at')
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'link')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )