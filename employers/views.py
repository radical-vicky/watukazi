from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import EmployerProfile
from jobs.models import JobRequest, JobMatch
from accounts.models import Profile

@login_required
def dashboard(request):
    # Check if user is employer
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Profile not found. Please contact support.")
        return redirect('accounts:home')
    
    if request.user.profile.user_type != 'employer':
        messages.error(request, "Access denied. This page is for employers only.")
        return redirect('accounts:home')
    
    # Create employer profile if it doesn't exist
    employer_profile, created = EmployerProfile.objects.get_or_create(user=request.user)
    if created:
        messages.info(request, "Welcome! Please complete your company profile.")
    
    # Get employer's jobs
    my_jobs = JobRequest.objects.filter(employer=request.user).order_by('-created_at')
    
    # Get statistics
    total_jobs = my_jobs.count()
    active_jobs = my_jobs.filter(status='open').count()
    completed_jobs = my_jobs.filter(status='completed').count()
    total_matches = JobMatch.objects.filter(job_request__employer=request.user).count()
    
    # Get recent job applications
    recent_matches = JobMatch.objects.filter(
        job_request__employer=request.user
    ).order_by('-created_at')[:10]
    
    context = {
        'profile': employer_profile,
        'my_jobs': my_jobs,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'total_matches': total_matches,
        'recent_matches': recent_matches,
    }
    return render(request, 'employers/dashboard.html', context)

@login_required
def edit_profile(request):
    """Edit company profile page"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'employer':
        messages.error(request, "Access denied.")
        return redirect('accounts:home')
    
    employer_profile, created = EmployerProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': employer_profile,
    }
    return render(request, 'employers/edit_profile.html', context)

@login_required
def update_company_info(request):
    if request.method == 'POST':
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'employer':
            messages.error(request, "Access denied.")
            return redirect('accounts:home')
        
        employer, created = EmployerProfile.objects.get_or_create(user=request.user)
        employer.company_name = request.POST.get('company_name', '')
        employer.business_registration = request.POST.get('business_registration', '')
        employer.website = request.POST.get('website', '')
        employer.save()
        
        # Update user profile
        profile = request.user.profile
        profile.location = request.POST.get('location', '')
        profile.save()
        
        # Update user email if changed
        new_email = request.POST.get('email')
        if new_email and new_email != request.user.email:
            request.user.email = new_email
            request.user.save()
        
        messages.success(request, "Company profile updated successfully!")
        return redirect('employers:dashboard')
    
    return redirect('employers:dashboard')