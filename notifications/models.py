from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('job_match', 'New Job Match'),
        ('application_accepted', 'Application Accepted'),
        ('application_rejected', 'Application Rejected'),
        ('job_completed', 'Job Completed'),
        ('rating_received', 'Rating Received'),
        ('new_applicant', 'New Applicant'),
        ('job_posted', 'Job Posted'),
        ('job_expiring', 'Job Expiring Soon'),
        ('profile_view', 'Profile Viewed'),
        ('message', 'New Message'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def get_notification_icon(self):
        icons = {
            'job_match': '📋',
            'application_accepted': '✅',
            'application_rejected': '❌',
            'job_completed': '🎉',
            'rating_received': '⭐',
            'new_applicant': '👤',
            'job_posted': '📢',
            'job_expiring': '⏰',
            'profile_view': '👁️',
            'message': '💬',
        }
        return icons.get(self.notification_type, '📢')
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, link='', sender=None):
        notification = cls.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
        
        # Send SMS notification
        try:
            from sms_simulator.utils import send_sms
            sms_message = f"{title}\n{message}\n\nReply HELP for commands"
            send_sms(recipient.profile.phone_number, sms_message)
        except Exception as e:
            print(f"SMS notification failed: {e}")
        
        return notification
    
    @classmethod
    def create_job_match_notification(cls, worker, job, match_score):
        title = f"New Job Match: {job.title}"
        message = f"A new job matching your skills has been posted.\n\n"
        message += f"📍 Location: {job.location}\n"
        message += f"💰 Budget: KES {job.budget if job.budget else 'Negotiable'}\n"
        message += f"🎯 Match Score: {match_score}%\n\n"
        message += f"Reply APPLY {job.id} to apply"
        link = reverse('jobs:job_detail', args=[job.id])
        return cls.create_notification(
            recipient=worker,
            notification_type='job_match',
            title=title,
            message=message,
            link=link,
            sender=job.employer
        )
    
    @classmethod
    def create_application_accepted_notification(cls, worker, job):
        title = f"Application Accepted: {job.title}"
        message = f"Congratulations! Your application has been accepted.\n\n"
        message += f"Employer: {job.employer.get_full_name()}\n"
        message += f"Contact: {job.employer.profile.phone_number}\n\n"
        message += f"Please contact the employer to discuss next steps."
        link = reverse('jobs:job_detail', args=[job.id])
        return cls.create_notification(
            recipient=worker,
            notification_type='application_accepted',
            title=title,
            message=message,
            link=link,
            sender=job.employer
        )
    
    @classmethod
    def create_new_applicant_notification(cls, employer, job, worker):
        title = f"New Applicant for {job.title}"
        message = f"{worker.get_full_name()} has applied for your job.\n\n"
        message += f"Worker Contact: {worker.profile.phone_number}\n"
        message += f"Worker Skills: {', '.join([s.name for s in worker.worker_profile.skills.all()][:3])}\n\n"
        message += f"Reply APPLICANTS {job.id} to view all applicants"
        link = reverse('jobs:job_detail', args=[job.id])
        return cls.create_notification(
            recipient=employer,
            notification_type='new_applicant',
            title=title,
            message=message,
            link=link,
            sender=worker
        )
    
    @classmethod
    def create_job_completed_notification(cls, worker, job, rating):
        title = f"Job Completed: {job.title}"
        message = f"Great work! Your job has been marked as completed.\n\n"
        message += f"Employer Rating: {rating}/5 stars\n\n"
        message += f"Thank you for your hard work!"
        link = reverse('jobs:job_detail', args=[job.id])
        return cls.create_notification(
            recipient=worker,
            notification_type='job_completed',
            title=title,
            message=message,
            link=link,
            sender=job.employer
        )
    
    @classmethod
    def create_rating_received_notification(cls, user, rating, feedback, from_user):
        title = f"New Rating Received"
        message = f"You have been rated {rating}/5 stars by {from_user.get_full_name()}.\n\n"
        if feedback:
            message += f"Feedback: {feedback}\n\n"
        message += f"Keep up the great work!"
        return cls.create_notification(
            recipient=user,
            notification_type='rating_received',
            title=title,
            message=message,
            link='',
            sender=from_user
        )