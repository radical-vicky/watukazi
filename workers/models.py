from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class SkillCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Skill Categories"
    
    def __str__(self):
        return self.name

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class WorkerProfile(models.Model):
    AVAILABILITY_STATUS = (
        ('available', 'Available for Work'),
        ('busy', 'Currently Busy'),
        ('away', 'Away/Temporarily Unavailable'),
        ('inactive', 'Inactive'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    skills = models.ManyToManyField(Skill, related_name='workers', blank=True)
    years_experience = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    availability_status = models.CharField(max_length=10, choices=AVAILABILITY_STATUS, default='available')
    bio = models.TextField(blank=True, help_text="Describe your skills and experience")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_jobs_completed = models.IntegerField(default=0)
    
    # Verification fields
    profile_image = models.ImageField(upload_to='worker_profiles/', null=True, blank=True)
    id_image = models.ImageField(upload_to='worker_ids/', null=True, blank=True, help_text="Upload your National ID or Passport")
    id_number = models.CharField(max_length=20, blank=True, help_text="National ID or Passport Number")
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.availability_status}"
    
    def update_rating(self):
        from jobs.models import JobMatch
        completed_jobs = JobMatch.objects.filter(worker=self.user, status='completed')
        if completed_jobs.exists():
            avg_rating = completed_jobs.aggregate(models.Avg('worker_rating'))['worker_rating__avg']
            self.rating = avg_rating or 0
            self.save()
    
    def get_top_skills(self, limit=5):
        return self.skills.all()[:limit]
    
    def is_verified(self):
        return self.verification_status == 'verified'
    
    def get_pending_confirmations(self):
        """Get jobs that the worker needs to confirm"""
        from jobs.models import JobMatch
        return JobMatch.objects.filter(
            worker=self.user, 
            status='accepted'
        ).filter(
            models.Q(response_deadline__isnull=True) | 
            models.Q(response_deadline__gte=models.functions.Now())
        )
    
    def get_upcoming_jobs(self):
        """Get confirmed jobs that are upcoming"""
        from jobs.models import JobMatch
        return JobMatch.objects.filter(
            worker=self.user,
            status='confirmed',
            report_time__gte=models.functions.Now()
        ).order_by('report_time')