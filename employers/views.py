from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from django.contrib.auth.models import User  # Add this import
from .models import EmployerProfile
from jobs.models import JobRequest, JobMatch
from accounts.models import Profile

@login_required
def dashboard(request):
    """Employer dashboard view"""
    print(f"Dashboard accessed by: {request.user.username}")
    print(f"Has profile: {hasattr(request.user, 'profile')}")
    
    # Ensure profile exists
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Profile not found. Please contact support.")
        return redirect('accounts:home')
    
    print(f"User type from profile: {request.user.profile.user_type}")
    
    # Check if employer profile exists, if yes, ensure user_type is employer
    if EmployerProfile.objects.filter(user=request.user).exists():
        if request.user.profile.user_type != 'employer':
            request.user.profile.user_type = 'employer'
            request.user.profile.save()
            print(f"Fixed user type to employer for {request.user.username}")
    
    # If still not employer, show error
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
    
    # Get completed jobs with ratings for display
    completed_matches = JobMatch.objects.filter(
        job_request__employer=request.user,
        status='completed'
    ).order_by('-updated_at')[:5]
    
    context = {
        'profile': employer_profile,
        'my_jobs': my_jobs,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'total_matches': total_matches,
        'recent_matches': recent_matches,
        'completed_matches': completed_matches,
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
        employer.company_description = request.POST.get('company_description', '')
        employer.company_logo = request.FILES.get('company_logo') or employer.company_logo
        employer.industry = request.POST.get('industry', '')
        employer.employee_count = request.POST.get('employee_count', '')
        employer.year_established = request.POST.get('year_established', '')
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
        
        # Update user name
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        if first_name or last_name:
            request.user.first_name = first_name or ''
            request.user.last_name = last_name or ''
            request.user.save()
        
        messages.success(request, "Company profile updated successfully!")
        return redirect('employers:dashboard')
    
    return redirect('employers:dashboard')

@login_required
def employer_profile_view(request, username=None):
    """View employer profile - public profile"""
    if username:
        employer_user = get_object_or_404(User, username=username)
        if employer_user.profile.user_type != 'employer':
            messages.error(request, "This user is not registered as an employer.")
            return redirect('accounts:home')
    else:
        employer_user = request.user
        if employer_user.profile.user_type != 'employer':
            messages.error(request, "You are not registered as an employer.")
            return redirect('accounts:home')
    
    # Get or create employer profile
    employer_profile, created = EmployerProfile.objects.get_or_create(user=employer_user)
    
    # Get employer's jobs
    jobs = JobRequest.objects.filter(employer=employer_user, status='open').order_by('-created_at')[:10]
    completed_jobs = JobRequest.objects.filter(employer=employer_user, status='completed').count()
    
    # Get ratings from completed jobs
    completed_matches = JobMatch.objects.filter(
        job_request__employer=employer_user,
        status='completed',
        employer_rating__isnull=False
    )
    
    total_rating = completed_matches.aggregate(Avg('employer_rating'))['employer_rating__avg'] or 0
    rating_count = completed_matches.count()
    
    # Get recent reviews
    recent_reviews = completed_matches.select_related('worker').order_by('-updated_at')[:5]
    
    context = {
        'employer': employer_profile,
        'employer_user': employer_user,
        'jobs': jobs,
        'total_jobs': JobRequest.objects.filter(employer=employer_user).count(),
        'completed_jobs': completed_jobs,
        'active_jobs': jobs.count(),
        'total_rating': total_rating,
        'rating_count': rating_count,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'employers/profile.html', context)

@login_required
def employer_public_profile(request, username):
    """Public employer profile - anyone can view"""
    employer_user = get_object_or_404(User, username=username)
    
    if employer_user.profile.user_type != 'employer':
        messages.error(request, "This user is not registered as an employer.")
        return redirect('accounts:home')
    
    employer_profile, created = EmployerProfile.objects.get_or_create(user=employer_user)
    
    # Get open jobs for this employer
    open_jobs = JobRequest.objects.filter(
        employer=employer_user,
        status='open'
    ).order_by('-created_at')[:10]
    
    # Get completed jobs count
    completed_jobs = JobRequest.objects.filter(
        employer=employer_user,
        status='completed'
    ).count()
    
    # Get ratings
    completed_matches = JobMatch.objects.filter(
        job_request__employer=employer_user,
        status='completed',
        employer_rating__isnull=False
    )
    
    total_rating = completed_matches.aggregate(Avg('employer_rating'))['employer_rating__avg'] or 0
    rating_count = completed_matches.count()
    
    context = {
        'employer': employer_profile,
        'employer_user': employer_user,
        'open_jobs': open_jobs,
        'total_jobs': JobRequest.objects.filter(employer=employer_user).count(),
        'completed_jobs': completed_jobs,
        'total_rating': total_rating,
        'rating_count': rating_count,
    }
    return render(request, 'employers/public_profile.html', context)