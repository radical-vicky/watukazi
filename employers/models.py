from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=200, blank=True)
    business_registration = models.CharField(max_length=100, blank=True, help_text="Business registration number")
    website = models.URLField(blank=True)
    company_description = models.TextField(blank=True, help_text="Describe your company and what you do")
    company_logo = models.ImageField(upload_to='employer_logos/', null=True, blank=True)
    industry = models.CharField(max_length=100, blank=True, help_text="e.g., Construction, Technology, Agriculture")
    employee_count = models.CharField(max_length=50, blank=True, choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees'),
    ])
    year_established = models.IntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_jobs_posted = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name or self.user.username
    
    def update_rating(self):
        from jobs.models import JobMatch
        completed_matches = JobMatch.objects.filter(
            job_request__employer=self.user,
            status='completed',
            employer_rating__isnull=False
        )
        if completed_matches.exists():
            avg_rating = completed_matches.aggregate(models.Avg('employer_rating'))['employer_rating__avg']
            self.rating = avg_rating or 0
            self.save()
    
    def get_rating_stars(self):
        """Return star rating display"""
        if self.rating == 0:
            return "No ratings yet"
        full_stars = int(self.rating)
        half_star = self.rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)
        return "⭐" * full_stars + ("½" if half_star else "") + "☆" * empty_stars