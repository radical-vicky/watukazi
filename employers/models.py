from django.db import models
from django.contrib.auth.models import User

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=100, blank=True)
    business_registration = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    total_jobs_posted = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    is_verified_business = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name or self.user.username
    
    def update_rating(self):
        from jobs.models import JobMatch
        completed_jobs = JobMatch.objects.filter(job_request__employer=self.user, status='completed')
        if completed_jobs.exists():
            avg_rating = completed_jobs.aggregate(models.Avg('employer_rating'))['employer_rating__avg']
            self.rating = avg_rating or 0
            self.save()