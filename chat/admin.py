from django.contrib import admin
from .models import Conversation, Message, MessageAttachment, ConversationReadReceipt

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'employer', 'worker', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['job__title', 'employer__username', 'worker__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'receiver', 'content_preview', 'sent_at', 'is_read']
    list_filter = ['is_read', 'sent_at']
    search_fields = ['content', 'sender__username', 'receiver__username']
    readonly_fields = ['sent_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message Preview'

@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'filename', 'file_size', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename']

@admin.register(ConversationReadReceipt)
class ConversationReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'user', 'last_read_at']
    list_filter = ['last_read_at']