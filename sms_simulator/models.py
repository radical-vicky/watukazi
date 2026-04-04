from django.db import models
from django.utils import timezone

class SMSLog(models.Model):
    DIRECTION_CHOICES = (
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    )
    
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    )
    
    phone_number = models.CharField(max_length=15, db_index=True)
    message = models.TextField()
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='outgoing')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['direction']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.direction} SMS to {self.phone_number} at {self.created_at}"
    
    def mark_as_delivered(self):
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error):
        self.status = 'failed'
        self.error_message = error
        self.save()