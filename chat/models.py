from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from jobs.models import JobRequest, JobMatch

class Conversation(models.Model):
    """Conversation between employer and worker for a specific job"""
    job = models.ForeignKey(JobRequest, on_delete=models.CASCADE, related_name='conversations')
    job_match = models.OneToOneField(JobMatch, on_delete=models.CASCADE, related_name='conversation', null=True, blank=True)
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employer_conversations')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='worker_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['job', 'employer', 'worker']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation: {self.job.title} - {self.worker.username}"
    
    def get_last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-sent_at').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(is_read=False, is_deleted=False).exclude(sender=user).count()
    
    def mark_as_read(self, user):
        self.messages.filter(is_read=False, is_deleted=False).exclude(sender=user).update(is_read=True)

class Message(models.Model):
    """Individual message in a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(max_length=2000)
    sent_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_receiver = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # Soft delete for both
    
    class Meta:
        ordering = ['sent_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.sent_at}"
    
    def save(self, *args, **kwargs):
        if self.is_read and not self.read_at:
            self.read_at = timezone.now()
        super().save(*args, **kwargs)
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class MessageAttachment(models.Model):
    """Optional attachments for messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField()  # Size in bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attachment: {self.filename}"

class ConversationReadReceipt(models.Model):
    """Track when users have read conversations"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['conversation', 'user']