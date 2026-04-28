from django.db import models
from django.contrib.auth.models import User
from workers.models import Skill
from django.utils import timezone
from datetime import timedelta

class JobRequest(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open for Applications'),
        ('matching', 'Matching in Progress'),
        ('matched', 'Workers Matched'),
        ('in_progress', 'Work in Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_requests')
    title = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.ManyToManyField(Skill, related_name='job_requests')
    location = models.CharField(max_length=100)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    duration_days = models.IntegerField(default=1, help_text="Estimated duration in days")
    
    def __str__(self):
        return f"{self.title} - {self.location}"
    
    def find_matching_workers(self):
        """AI-based matching algorithm with location bonus"""
        matching_workers = []
        required_skill_ids = list(self.required_skills.values_list('id', flat=True))
        
        if not required_skill_ids:
            return []
        
        workers = User.objects.filter(
            profile__user_type='worker',
            worker_profile__availability_status='available'
        ).select_related('worker_profile')
        
        for worker in workers:
            worker_skills = list(worker.worker_profile.skills.values_list('id', flat=True))
            matching_skills = set(required_skill_ids) & set(worker_skills)
            
            if required_skill_ids:
                match_score = (len(matching_skills) / len(required_skill_ids)) * 100
            else:
                match_score = 0
            
            # Location matching (bonus up to 20%)
            location_bonus = 0
            if worker.profile.location and self.location:
                if worker.profile.location.lower() == self.location.lower():
                    location_bonus = 20
                elif worker.profile.location.lower() in self.location.lower() or self.location.lower() in worker.profile.location.lower():
                    location_bonus = 10
            
            final_score = match_score + location_bonus
            
            if match_score >= 50:  # 50% skill match threshold
                matching_workers.append({
                    'worker': worker,
                    'match_score': final_score,
                    'matching_skills_count': len(matching_skills),
                    'total_skills_required': len(required_skill_ids),
                    'location_bonus': location_bonus
                })
        
        # Sort by match score descending
        matching_workers.sort(key=lambda x: x['match_score'], reverse=True)
        return matching_workers
    
    def auto_match_workers(self, max_matches=10):
        """Automatically match and notify workers via SMS"""
        matches = self.find_matching_workers()
        
        created_matches = []
        for match_data in matches[:max_matches]:
            job_match, created = JobMatch.objects.get_or_create(
                job_request=self,
                worker=match_data['worker'],
                defaults={'match_score': match_data['match_score']}
            )
            
            if created:
                # Send SMS notification to worker
                try:
                    from sms_simulator.utils import send_sms
                    message = f"🔔 NEW JOB ALERT!\n\n"
                    message += f"Job: {self.title}\n"
                    message += f"Location: {self.location}\n"
                    message += f"Budget: KES {self.budget if self.budget else 'Negotiable'}\n"
                    message += f"Match: {match_data['match_score']:.0f}%\n"
                    message += f"Reply: APPLY {self.id} to apply\n"
                    message += f"Or login: http://127.0.0.1:8000/jobs/{self.id}/"
                    
                    send_sms(match_data['worker'].profile.phone_number, message)
                except Exception as e:
                    print(f"SMS sending failed: {e}")
                created_matches.append(job_match)
        
        if created_matches:
            self.status = 'matching'
            self.save()
        
        return created_matches


class JobMatch(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Worker Response'),
        ('accepted', 'Accepted by Worker'),
        ('rejected', 'Rejected by Worker'),
        ('confirmed', 'Confirmed by Employer'),
        ('started', 'Work Started'),
        ('completed', 'Work Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    job_request = models.ForeignKey(JobRequest, on_delete=models.CASCADE, related_name='matches')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_matches')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    match_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    worker_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    employer_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    worker_feedback = models.TextField(blank=True)
    employer_feedback = models.TextField(blank=True)
    
    # New fields for directions and procedures
    directions = models.TextField(blank=True, null=True, help_text="Directions for the worker to reach the job site")
    procedures = models.TextField(blank=True, null=True, help_text="Procedures or instructions for the worker")
    access_code = models.CharField(max_length=50, blank=True, null=True, help_text="Access code or password if needed")
    contact_person = models.CharField(max_length=200, blank=True, null=True, help_text="Contact person name")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Contact phone number")
    response_deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline for worker to confirm/respond")
    report_time = models.DateTimeField(null=True, blank=True, help_text="When worker should report to site")
    
    def __str__(self):
        return f"Match: {self.job_request.title} - {self.worker.username}"
    
    def accept_by_worker(self):
        self.status = 'accepted'
        self.save()
        
        # Send SMS to employer
        try:
            from sms_simulator.utils import send_sms
            message = f"✅ Worker {self.worker.get_full_name()} has accepted your job!\n"
            message += f"Job: {self.job_request.title}\n"
            message += f"Contact: {self.worker.profile.phone_number}\n"
            message += f"Login to provide directions: http://127.0.0.1:8000/jobs/{self.job_request.id}/"
            send_sms(self.job_request.employer.profile.phone_number, message)
        except Exception as e:
            print(f"SMS sending failed: {e}")
    
    def send_acceptance_details(self):
        """Send SMS with directions and procedures when employer accepts worker"""
        from sms_simulator.utils import send_sms
        
        message = f"✅ JOB ACCEPTED: {self.job_request.title}\n\n"
        
        if self.contact_person:
            message += f"📞 Contact: {self.contact_person} - {self.contact_phone}\n\n"
        
        if self.directions:
            message += f"📍 DIRECTIONS:\n{self.directions}\n\n"
        
        if self.procedures:
            message += f"📋 PROCEDURES:\n{self.procedures}\n\n"
        
        if self.access_code:
            message += f"🔑 Access Code: {self.access_code}\n\n"
        
        if self.report_time:
            message += f"⏰ Report by: {self.report_time.strftime('%Y-%m-%d %H:%M')}\n"
        
        if self.response_deadline:
            message += f"⚠️ Confirm before: {self.response_deadline.strftime('%Y-%m-%d %H:%M')}\n"
        
        message += "\nReply: CONFIRM to accept or CANCEL to decline"
        
        send_sms(self.worker.profile.phone_number, message)
    
    def confirm_by_worker(self):
        """Worker confirms after receiving directions"""
        self.status = 'confirmed'
        self.save()
        
        # Send SMS to employer
        try:
            from sms_simulator.utils import send_sms
            message = f"✅ Worker {self.worker.get_full_name()} has confirmed job '{self.job_request.title}'.\n"
            message += f"They will report as directed."
            send_sms(self.job_request.employer.profile.phone_number, message)
        except Exception as e:
            print(f"SMS sending failed: {e}")
    
    def complete_job(self, rating=None, feedback=None):
        """Employer completes job and rates worker"""
        self.status = 'completed'
        if rating:
            self.worker_rating = rating
        if feedback:
            self.employer_feedback = feedback
        self.save()
        
        # Update worker stats
        worker_profile = self.worker.worker_profile
        worker_profile.total_jobs_completed += 1
        worker_profile.save()
        worker_profile.update_rating()
        
        # Update employer stats
        try:
            from employers.models import EmployerProfile
            employer_profile, created = EmployerProfile.objects.get_or_create(user=self.job_request.employer)
            employer_profile.total_jobs_posted += 1
            employer_profile.save()
            employer_profile.update_rating()
        except Exception as e:
            print(f"Employer stats update failed: {e}")
        
        # Update job status
        self.job_request.status = 'completed'
        self.job_request.save()
        
        # Send SMS notification to worker
        try:
            from sms_simulator.utils import send_sms
            message = f"🎉 Job Completed!\n"
            message += f"Job: {self.job_request.title}\n"
            message += f"Rating: {rating}/5 stars\n"
            if feedback:
                message += f"Feedback: {feedback}\n"
            message += f"Thank you for your hard work!"
            send_sms(self.worker.profile.phone_number, message)
        except Exception as e:
            print(f"SMS sending failed: {e}")
    
    def rate_employer(self, rating, feedback=''):
        """Worker rates employer after job completion"""
        self.employer_rating = rating
        self.worker_feedback = feedback
        self.save()
        
        # Update employer's rating
        employer_profile = self.job_request.employer.employer_profile
        employer_profile.update_rating()
        
        # Send SMS notification to employer
        try:
            from sms_simulator.utils import send_sms
            message = f"⭐ New Rating Received!\n"
            message += f"Worker: {self.worker.get_full_name()}\n"
            message += f"Rating: {rating}/5 stars\n"
            if feedback:
                message += f"Feedback: {feedback}\n"
            send_sms(self.job_request.employer.profile.phone_number, message)
        except Exception as e:
            print(f"SMS sending failed: {e}")
    
    def get_worker_rating_display(self):
        if self.worker_rating:
            stars = "⭐" * self.worker_rating
            return f"{self.worker_rating}/5 {stars}"
        return "Not rated yet"
    
    def get_employer_rating_display(self):
        if self.employer_rating:
            stars = "⭐" * self.employer_rating
            return f"{self.employer_rating}/5 {stars}"
        return "Not rated yet"
    
    def is_deadline_expired(self):
        """Check if response deadline has passed"""
        if self.response_deadline:
            return timezone.now() > self.response_deadline
        return False
    
    def get_directions_summary(self):
        """Get a short summary of directions"""
        if self.directions:
            return self.directions[:150] + '...' if len(self.directions) > 150 else self.directions
        return "No directions provided"