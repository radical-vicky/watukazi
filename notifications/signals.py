from django.db.models.signals import post_save
from django.dispatch import receiver
from jobs.models import JobRequest, JobMatch
from workers.models import WorkerProfile

@receiver(post_save, sender=JobRequest)
def notify_workers_on_job_post(sender, instance, created, **kwargs):
    """Notify workers when a new job is posted"""
    if created:
        from .models import Notification
        # Find matching workers
        matches = instance.find_matching_workers()
        for match in matches[:10]:  # Notify top 10 matches
            Notification.create_job_match_notification(
                worker=match['worker'],
                job=instance,
                match_score=match['match_score']
            )

@receiver(post_save, sender=JobMatch)
def notify_on_application(sender, instance, created, **kwargs):
    """Notify employer when worker applies"""
    if created:
        from .models import Notification
        Notification.create_new_applicant_notification(
            employer=instance.job_request.employer,
            job=instance.job_request,
            worker=instance.worker
        )