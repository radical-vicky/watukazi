from django.contrib import admin
from .models import SMSLog

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'message_preview', 'direction', 'status', 'created_at')
    list_filter = ('direction', 'status', 'created_at')
    search_fields = ('phone_number', 'message')
    readonly_fields = ('created_at', 'delivered_at')
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions