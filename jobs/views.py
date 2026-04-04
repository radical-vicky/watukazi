from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import JobRequest, JobMatch
from workers.models import Skill

def public_jobs(request):
    """Public job listing - no login required"""
    jobs = JobRequest.objects.filter(status='open').order_by('-created_at')
    
    # Get unique locations for filter
    locations = JobRequest.objects.filter(status='open').values_list('location', flat=True).distinct()
    
    # Get skills for filter
    skills = Skill.objects.all()
    
    # Apply filters
    location_filter = request.GET.get('location', '')
    skill_filter = request.GET.get('skill', '')
    
    if location_filter:
        jobs = jobs.filter(location__icontains=location_filter)
    
    if skill_filter:
        try:
            skill = Skill.objects.get(id=skill_filter)
            jobs = jobs.filter(required_skills=skill)
        except Skill.DoesNotExist:
            pass
    
    context = {
        'jobs': jobs,
        'locations': locations,
        'skills': skills,
        'location_filter': location_filter,
        'skill_filter': skill_filter,
        'total_count': jobs.count(),
    }
    return render(request, 'jobs/public_jobs.html', context)



@login_required
def create_job(request):
    if request.user.profile.user_type != 'employer':
        messages.error(request, "Only employers can create job postings")
        return redirect('/')
    
    if request.method == 'POST':
        try:
            job = JobRequest.objects.create(
                employer=request.user,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                location=request.POST.get('location'),
                budget=request.POST.get('budget') or None,
                duration_days=int(request.POST.get('duration_days', 1)),
            )
            
            skill_ids = request.POST.getlist('required_skills')
            for skill_id in skill_ids:
                try:
                    skill = Skill.objects.get(id=skill_id)
                    job.required_skills.add(skill)
                except Skill.DoesNotExist:
                    pass
            
            messages.success(request, "Job posted successfully! Matching workers will be notified.")
            
            # Auto-match workers
            matches_created = job.auto_match_workers()
            if matches_created:
                messages.info(request, f"Found {len(matches_created)} matching workers who have been notified via SMS.")
            else:
                messages.warning(request, "No matching workers found at the moment. Your job is still open for applications.")
            
            return redirect('employers:dashboard')
        except Exception as e:
            messages.error(request, f"Error creating job: {str(e)}")
            return redirect('jobs:create_job')
    
    context = {
        'skills': Skill.objects.all(),
    }
    return render(request, 'jobs/create_job.html', context)

@login_required
def job_detail(request, job_id):
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Allow access to:
    # 1. The employer who posted the job
    # 2. Admin users
    # 3. Workers (they can view jobs to apply)
    if request.user != job.employer and request.user.profile.user_type not in ['admin', 'worker']:
        messages.error(request, "Access denied")
        return redirect('/')
    
    matches = job.matches.all().order_by('-match_score')
    
    # Get user's application for this job (if worker)
    user_matches = []
    has_applied = False
    if request.user.profile.user_type == 'worker':
        user_matches = JobMatch.objects.filter(worker=request.user, job_request=job)
        has_applied = user_matches.exists()
    
    context = {
        'job': job,
        'matches': matches,
        'user_matches': user_matches,
        'has_applied': has_applied,
    }
    return render(request, 'jobs/job_detail.html', context)

@login_required
def accept_match(request, match_id):
    """Employer accepts a worker's application"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the employer owns this job
    if request.user != match.job_request.employer:
        messages.error(request, "Access denied. You don't own this job posting.")
        return redirect('/')
    
    if request.method == 'POST':
        match.status = 'accepted'
        match.save()
        
        # Update job status
        match.job_request.status = 'matched'
        match.job_request.save()
        
        # Send SMS notification to worker
        from sms_simulator.utils import send_sms
        message = f"Congratulations! Your application for '{match.job_request.title}' has been accepted. Contact employer at {match.job_request.employer.profile.phone_number}"
        send_sms(match.worker.profile.phone_number, message)
        
        messages.success(request, f"Worker {match.worker.get_full_name()} has been notified via SMS")
    
    return redirect('jobs:job_detail', job_id=match.job_request.id)

@login_required
def reject_match(request, match_id):
    """Employer rejects a worker's application"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the employer owns this job
    if request.user != match.job_request.employer:
        messages.error(request, "Access denied. You don't own this job posting.")
        return redirect('/')
    
    if request.method == 'POST':
        match.status = 'rejected'
        match.save()
        
        # Send SMS notification to worker
        from sms_simulator.utils import send_sms
        message = f"Thank you for your interest in '{match.job_request.title}'. The employer has selected another candidate for this position."
        send_sms(match.worker.profile.phone_number, message)
        
        messages.info(request, f"Application from {match.worker.get_full_name()} has been rejected.")
    
    return redirect('jobs:job_detail', job_id=match.job_request.id)

@login_required
def worker_respond_match(request, match_id):
    """Worker responds to a job match (accept or reject)"""
    # Handle case when match_id is 0 (new application)
    if match_id == 0:
        job_id = request.POST.get('job_id')
        if job_id:
            job = get_object_or_404(JobRequest, id=job_id)
            
            # Check if already applied
            if JobMatch.objects.filter(job_request=job, worker=request.user).exists():
                messages.warning(request, "You have already applied for this job.")
                return redirect('jobs:job_detail', job_id=job.id)
            
            # Create application
            match = JobMatch.objects.create(
                job_request=job,
                worker=request.user,
                status='pending',
                match_score=50
            )
            messages.success(request, f"You have applied for '{job.title}'. The employer will contact you.")
            return redirect('jobs:job_detail', job_id=job.id)
    
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the worker owns this match
    if request.user != match.worker:
        messages.error(request, "Access denied")
        return redirect('/')
    
    if request.method == 'POST':
        response = request.POST.get('response')
        
        if response == 'accept':
            match.accept_by_worker()
            messages.success(request, "You have accepted the job! The employer will contact you.")
        elif response == 'reject':
            match.status = 'rejected'
            match.save()
            messages.info(request, "You have declined the job.")
    
    return redirect('workers:dashboard')

@login_required
def complete_job(request, match_id):
    """Employer marks a job as completed and rates the worker"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the employer owns this job
    if request.user != match.job_request.employer:
        messages.error(request, "Access denied")
        return redirect('/')
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        feedback = request.POST.get('feedback', '')
        
        if rating >= 1 and rating <= 5:
            match.complete_job(rating=rating, feedback=feedback)
            messages.success(request, f"Job marked as completed! You rated the worker {rating}/5 stars.")
        else:
            messages.error(request, "Please provide a valid rating (1-5 stars).")
    
    return redirect('jobs:job_detail', job_id=match.job_request.id)

@login_required
def rate_employer(request, match_id):
    """Worker rates the employer after job completion"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the worker owns this match
    if request.user != match.worker:
        messages.error(request, "Access denied")
        return redirect('/')
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        feedback = request.POST.get('feedback', '')
        
        if rating >= 1 and rating <= 5:
            match.rate_employer(rating=rating, feedback=feedback)
            messages.success(request, f"Thank you for rating the employer {rating}/5 stars!")
        else:
            messages.error(request, "Please provide a valid rating (1-5 stars).")
    
    return redirect('jobs:job_detail', job_id=match.job_request.id)

@login_required
def my_jobs(request):
    """View all jobs posted by the employer"""
    if request.user.profile.user_type != 'employer':
        messages.error(request, "Access denied")
        return redirect('/')
    
    jobs = JobRequest.objects.filter(employer=request.user).order_by('-created_at')
    
    context = {
        'jobs': jobs,
        'active_count': jobs.filter(status='open').count(),
        'completed_count': jobs.filter(status='completed').count(),
        'total_count': jobs.count(),
    }
    return render(request, 'jobs/my_jobs.html', context)

@login_required
def my_applications(request):
    """View all job applications by the worker"""
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Access denied")
        return redirect('/')
    
    applications = JobMatch.objects.filter(worker=request.user).select_related('job_request').order_by('-created_at')
    
    context = {
        'applications': applications,
        'pending_count': applications.filter(status='pending').count(),
        'accepted_count': applications.filter(status='accepted').count(),
        'completed_count': applications.filter(status='completed').count(),
    }
    return render(request, 'jobs/my_applications.html', context)

@login_required
def edit_job(request, job_id):
    """Edit an existing job posting"""
    job = get_object_or_404(JobRequest, id=job_id)
    
    if request.user != job.employer:
        messages.error(request, "Access denied")
        return redirect('/')
    
    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.description = request.POST.get('description')
        job.location = request.POST.get('location')
        job.budget = request.POST.get('budget') or None
        job.duration_days = int(request.POST.get('duration_days', 1))
        
        # Update skills
        job.required_skills.clear()
        skill_ids = request.POST.getlist('required_skills')
        for skill_id in skill_ids:
            try:
                skill = Skill.objects.get(id=skill_id)
                job.required_skills.add(skill)
            except Skill.DoesNotExist:
                pass
        
        job.save()
        messages.success(request, "Job updated successfully!")
        return redirect('jobs:job_detail', job_id=job.id)
    
    context = {
        'job': job,
        'skills': Skill.objects.all(),
    }
    return render(request, 'jobs/edit_job.html', context)

@login_required
def delete_job(request, job_id):
    """Delete/cancel a job posting"""
    job = get_object_or_404(JobRequest, id=job_id)
    
    if request.user != job.employer:
        messages.error(request, "Access denied")
        return redirect('/')
    
    if request.method == 'POST':
        job.status = 'cancelled'
        job.save()
        messages.success(request, "Job has been cancelled.")
        return redirect('employers:dashboard')
    
    return redirect('jobs:job_detail', job_id=job.id)

@login_required
def search_jobs(request):
    """Search for jobs based on skills and location"""
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Access denied")
        return redirect('/')
    
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    jobs = JobRequest.objects.filter(status='open')
    
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    context = {
        'jobs': jobs,
        'query': query,
        'location': location,
        'total_count': jobs.count(),
    }
    return render(request, 'jobs/search_jobs.html', context)