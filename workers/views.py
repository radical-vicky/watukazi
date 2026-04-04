from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
from .models import WorkerProfile, Skill, SkillCategory
from .forms import WorkerProfileForm, SkillSelectionForm
from jobs.models import JobRequest, JobMatch
import random
import string

@login_required
def dashboard(request):
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Access denied. Worker dashboard only.")
        return redirect('/')
    
    worker_profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    if created:
        messages.info(request, "Welcome! Please complete your profile and verify your identity.")
    
    if worker_profile.verification_status == 'pending' and worker_profile.id_number and worker_profile.id_image:
        messages.warning(request, "Your account is pending verification. Request verification to get verified.")
    elif worker_profile.verification_status == 'pending':
        messages.info(request, "Please upload your ID to get verified.")
    elif worker_profile.verification_status == 'verified':
        messages.success(request, "Your account is verified! Employers trust verified workers more.")
    
    worker_skills = worker_profile.skills.all()
    available_jobs = JobRequest.objects.filter(
        status='open',
        location__icontains=request.user.profile.location
    )
    
    if worker_skills.exists():
        available_jobs = available_jobs.filter(required_skills__in=worker_skills).distinct()
    
    available_jobs = available_jobs.order_by('-created_at')[:10]
    my_jobs = JobMatch.objects.filter(worker=request.user).order_by('-created_at')
    
    recommended_jobs = []
    all_open_jobs = JobRequest.objects.filter(status='open').exclude(id__in=my_jobs.values('job_request_id'))
    
    for job in all_open_jobs:
        job_skills = job.required_skills.all()
        if worker_skills.exists() and job_skills.exists():
            matching_skills = set(worker_skills) & set(job_skills)
            match_score = (len(matching_skills) / job_skills.count()) * 100 if job_skills.count() > 0 else 0
            if match_score >= 50:
                recommended_jobs.append({'job': job, 'match_score': match_score})
    
    context = {
        'profile': worker_profile,
        'available_jobs': available_jobs,
        'my_jobs': my_jobs,
        'recommended_jobs': sorted(recommended_jobs, key=lambda x: x['match_score'], reverse=True)[:5],
        'skills': Skill.objects.all(),
        'skill_categories': SkillCategory.objects.all(),
        'worker_skills': worker_skills,
    }
    return render(request, 'workers/dashboard.html', context)

@login_required
def update_availability(request):
    if request.method == 'POST':
        if request.user.profile.user_type != 'worker':
            messages.error(request, "Only workers can update availability.")
            return redirect('/')
        
        worker_profile, created = WorkerProfile.objects.get_or_create(user=request.user)
        status = request.POST.get('status')
        worker_profile.availability_status = status
        worker_profile.save()
        messages.success(request, f"Availability updated to {worker_profile.get_availability_status_display()}")
    return redirect('workers:dashboard')

@login_required
def add_skills(request):
    if request.method == 'POST':
        if request.user.profile.user_type != 'worker':
            messages.error(request, "Only workers can add skills.")
            return redirect('/')
        
        worker_profile, created = WorkerProfile.objects.get_or_create(user=request.user)
        skills = request.POST.getlist('skills')
        worker_profile.skills.clear()
        for skill_id in skills:
            try:
                skill = Skill.objects.get(id=skill_id)
                worker_profile.skills.add(skill)
            except Skill.DoesNotExist:
                pass
        messages.success(request, f"Skills updated successfully! You have {worker_profile.skills.count()} skills.")
    return redirect('workers:dashboard')

@login_required
def worker_profile_view(request, username=None):
    if username:
        worker_user = get_object_or_404(User, username=username)
        if worker_user.profile.user_type != 'worker':
            messages.error(request, "This user is not a worker.")
            return redirect('/')
    else:
        worker_user = request.user
        if worker_user.profile.user_type != 'worker':
            messages.error(request, "You are not registered as a worker.")
            return redirect('/')
    
    worker, created = WorkerProfile.objects.get_or_create(user=worker_user)
    completed_jobs = JobMatch.objects.filter(worker=worker_user, status='completed')
    
    context = {
        'worker': worker,
        'completed_jobs': completed_jobs,
        'skills': worker.skills.all(),
    }
    return render(request, 'workers/profile.html', context)

@login_required
def edit_bio(request):
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Only workers can edit worker profiles.")
        return redirect('/')
    
    worker, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, request.FILES, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('workers:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WorkerProfileForm(instance=worker)
    
    context = {
        'form': form,
        'worker': worker,
    }
    return render(request, 'workers/edit_bio.html', context)

@login_required
def manage_skills(request):
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Only workers can manage skills.")
        return redirect('/')
    
    worker, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        skills = request.POST.getlist('skills')
        worker.skills.clear()
        for skill_id in skills:
            try:
                skill = Skill.objects.get(id=skill_id)
                worker.skills.add(skill)
            except Skill.DoesNotExist:
                pass
        messages.success(request, f"Your skills have been updated! You have {worker.skills.count()} skills.")
        return redirect('workers:profile')
    
    context = {
        'worker': worker,
        'skills': worker.skills.all(),
        'all_skills': Skill.objects.all(),
        'skill_categories': SkillCategory.objects.all(),
    }
    return render(request, 'workers/manage_skills.html', context)

@login_required
def request_verification(request):
    """Request SMS verification code"""
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Only workers can request verification.")
        return redirect('/')
    
    worker = request.user.worker_profile
    
    if request.method == 'POST':
        code = ''.join(random.choices(string.digits, k=6))
        worker.verification_code = code
        worker.save()
        
        from sms_simulator.utils import send_sms
        message = f"WATUKAZI VERIFICATION\nYour verification code is: {code}\nEnter this code on the website to verify your account."
        send_sms(request.user.profile.phone_number, message)
        
        messages.success(request, f"Verification code sent to {request.user.profile.phone_number}")
        return redirect('workers:verify_code')
    
    return render(request, 'workers/request_verification.html', {'worker': worker})

@login_required
def verify_code(request):
    """Verify SMS code"""
    if request.user.profile.user_type != 'worker':
        messages.error(request, "Only workers can verify.")
        return redirect('/')
    
    worker = request.user.worker_profile
    
    if request.method == 'POST':
        code = request.POST.get('code')
        
        if worker.verification_code == code:
            worker.verification_status = 'verified'
            worker.verified_at = timezone.now()
            worker.verification_code = None
            worker.save()
            messages.success(request, "Your account has been verified! Employers can now trust your profile.")
            return redirect('workers:dashboard')
        else:
            messages.error(request, "Invalid verification code. Please try again.")
    
    return render(request, 'workers/verify_code.html')