from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import JobRequest, JobMatch
from workers.models import Skill
from chat.models import Conversation  # Add this import

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
                
                # Create conversations with matched workers automatically
                for match in matches_created:
                    Conversation.objects.get_or_create(
                        job=job,
                        employer=request.user,
                        worker=match.worker,
                        defaults={'job_match': match}
                    )
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
    user_match = None
    existing_conversation = None
    
    if request.user.profile.user_type == 'worker':
        user_matches = JobMatch.objects.filter(worker=request.user, job_request=job)
        has_applied = user_matches.exists()
        if has_applied:
            user_match = user_matches.first()
            # Check if conversation exists
            existing_conversation = Conversation.objects.filter(job=job, worker=request.user).first()
    
    # Check if employer can start conversations
    can_start_conversation = False
    if request.user == job.employer:
        can_start_conversation = True
    
    context = {
        'job': job,
        'matches': matches,
        'user_matches': user_matches,
        'has_applied': has_applied,
        'user_match': user_match,
        'existing_conversation': existing_conversation,
        'can_start_conversation': can_start_conversation,
    }
    return render(request, 'jobs/job_detail.html', context)


@login_required
def accept_match(request, match_id):
    """Employer accepts a worker's application and provides directions"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    # Check if the employer owns this job
    if request.user != match.job_request.employer:
        messages.error(request, "Access denied. You don't own this job posting.")
        return redirect('/')
    
    if request.method == 'POST':
        # Get acceptance details from form
        directions = request.POST.get('directions', '')
        procedures = request.POST.get('procedures', '')
        contact_person = request.POST.get('contact_person', '')
        contact_phone = request.POST.get('contact_phone', '')
        access_code = request.POST.get('access_code', '')
        report_date = request.POST.get('report_date', '')
        report_time = request.POST.get('report_time', '')
        deadline_date = request.POST.get('deadline_date', '')
        deadline_time = request.POST.get('deadline_time', '')
        
        # Save details to match
        match.directions = directions
        match.procedures = procedures
        match.contact_person = contact_person or match.job_request.employer.get_full_name()
        match.contact_phone = contact_phone or match.job_request.employer.profile.phone_number
        match.access_code = access_code
        
        # Set report deadline
        if report_date and report_time:
            try:
                report_datetime = datetime.strptime(f"{report_date} {report_time}", "%Y-%m-%d %H:%M")
                match.report_time = timezone.make_aware(report_datetime)
            except ValueError:
                pass
        
        # Set response deadline
        if deadline_date and deadline_time:
            try:
                deadline_datetime = datetime.strptime(f"{deadline_date} {deadline_time}", "%Y-%m-%d %H:%M")
                match.response_deadline = timezone.make_aware(deadline_datetime)
            except ValueError:
                pass
        else:
            # Default deadline: 24 hours from now
            match.response_deadline = timezone.now() + timedelta(days=1)
        
        match.status = 'accepted'
        match.save()
        
        # Update job status
        match.job_request.status = 'matched'
        match.job_request.save()
        
        # Create or get conversation
        conversation, created = Conversation.objects.get_or_create(
            job=match.job_request,
            employer=request.user,
            worker=match.worker,
            defaults={'job_match': match}
        )
        
        # Send a message in chat with acceptance details
        from chat.models import Message
        welcome_message = f"""🎉 **Congratulations! You have been accepted for this job!**

**Job Details:**
📋 Title: {match.job_request.title}
📍 Location: {match.job_request.location}
💰 Budget: {match.job_request.budget} KES

**Contact Information:**
👤 Contact Person: {contact_person or match.job_request.employer.get_full_name()}
📞 Phone: {contact_phone or match.job_request.employer.profile.phone_number}

**Directions:**
{directions or 'Will be provided separately'}

**Procedures:**
{procedures or 'Will be discussed'}

{f'🔑 Access Code: {access_code}' if access_code else ''}

{f'⏰ Report Time: {match.report_time.strftime("%Y-%m-%d %H:%M") if match.report_time else "As agreed"}'}

Please respond to this message to confirm your acceptance.
"""
        
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=match.worker,
            content=welcome_message
        )
        
        # Send SMS with directions
        match.send_acceptance_details()
        
        # Also send email if available
        if match.worker.email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                
                email_body = f"""
You have been accepted for the job: {match.job_request.title}

CONTACT INFORMATION:
Contact Person: {contact_person or match.job_request.employer.get_full_name()}
Phone: {contact_phone or match.job_request.employer.profile.phone_number}

DIRECTIONS:
{directions or 'Not provided'}

PROCEDURES:
{procedures or 'Not provided'}

{'ACCESS CODE: ' + access_code if access_code else ''}

REPORT TIME: {match.report_time.strftime('%Y-%m-%d %H:%M') if match.report_time else 'As agreed with employer'}
RESPONSE DEADLINE: {match.response_deadline.strftime('%Y-%m-%d %H:%M') if match.response_deadline else 'Please confirm ASAP'}

Please confirm your acceptance by replying CONFIRM to the SMS, responding in the chat, or logging into your account.

Watukazi Team
                """
                
                send_mail(
                    f'Job Accepted: {match.job_request.title}',
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [match.worker.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
        
        messages.success(request, f"Worker {match.worker.get_full_name()} has been notified via SMS and chat with directions and procedures.")
    
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
        
        # Send rejection message in chat if conversation exists
        conversation = Conversation.objects.filter(
            job=match.job_request,
            employer=request.user,
            worker=match.worker
        ).first()
        
        if conversation:
            from chat.models import Message
            rejection_message = f"""Thank you for your interest in the position '{match.job_request.title}'.

After careful consideration, we have decided to move forward with another candidate for this role.

We appreciate your interest and encourage you to apply for other positions that match your skills.

Best regards,
{match.job_request.employer.get_full_name()}
"""
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=match.worker,
                content=rejection_message
            )
        
        # Send SMS notification to worker
        from sms_simulator.utils import send_sms
        message = f"Thank you for your interest in '{match.job_request.title}'. The employer has selected another candidate for this position."
        send_sms(match.worker.profile.phone_number, message)
        
        messages.info(request, f"Application from {match.worker.get_full_name()} has been rejected.")
    
    return redirect('jobs:job_detail', job_id=match.job_request.id)


@login_required
def worker_confirm_job(request, match_id):
    """Worker confirms acceptance after receiving directions"""
    match = get_object_or_404(JobMatch, id=match_id)
    
    if request.user != match.worker:
        messages.error(request, "Access denied")
        return redirect('workers:dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            match.status = 'confirmed'
            match.save()
            
            # Send confirmation message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                worker=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                confirmation_message = f"""✅ **Job Confirmed!**

I, {match.worker.get_full_name()}, confirm my acceptance for the position '{match.job_request.title}'.

I will report at the specified time and location as directed.

Thank you for this opportunity."""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.job_request.employer,
                    content=confirmation_message
                )
            
            # Notify employer
            from sms_simulator.utils import send_sms
            message = f"✅ Worker {match.worker.get_full_name()} has confirmed acceptance for job '{match.job_request.title}'. They will report as directed."
            send_sms(match.job_request.employer.profile.phone_number, message)
            
            messages.success(request, "You have confirmed the job. Please report at the specified time and location.")
            
        elif action == 'cancel':
            match.status = 'cancelled'
            match.save()
            
            # Send cancellation message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                worker=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                cancellation_message = f"""❌ **Job Cancellation**

Unfortunately, I must cancel my acceptance for the position '{match.job_request.title}'.

Reason: {request.POST.get('cancellation_reason', 'Not specified')}

I apologize for any inconvenience this may cause."""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.job_request.employer,
                    content=cancellation_message
                )
            
            # Notify employer
            from sms_simulator.utils import send_sms
            message = f"❌ Worker {match.worker.get_full_name()} has cancelled job '{match.job_request.title}'."
            send_sms(match.job_request.employer.profile.phone_number, message)
            
            messages.info(request, "You have cancelled this job.")
    
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
            
            # Notify employer via chat
            conversation, created = Conversation.objects.get_or_create(
                job=job,
                employer=job.employer,
                worker=request.user,
                defaults={'job_match': match}
            )
            
            from chat.models import Message
            application_message = f"""📝 **New Job Application**

I, {request.user.get_full_name()|default:request.user.username}, am applying for the position:

**{job.title}**

**My Skills:** {', '.join([skill.name for skill in request.user.profile.skills.all()])}

**Location:** {request.user.profile.location or 'Not specified'}

Please review my application and let me know if you need any additional information.

Thank you for considering my application."""
            
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=job.employer,
                content=application_message
            )
            
            messages.success(request, f"You have applied for '{job.title}'. The employer will contact you via chat.")
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
            
            # Send acceptance message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                worker=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                accept_message = f"""✅ **Job Offer Accepted**

I am pleased to accept the job offer for:

**{match.job_request.title}**

I look forward to working with you on this project.

Please let me know the next steps and any additional information I may need."""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.job_request.employer,
                    content=accept_message
                )
            
            messages.success(request, "You have accepted the job! The employer will contact you with directions.")
            
        elif response == 'reject':
            match.status = 'rejected'
            match.save()
            
            # Send rejection message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                worker=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                reject_message = f"""❌ **Job Offer Declined**

Thank you for the offer, but I must respectfully decline the position:

**{match.job_request.title}**

Reason: {request.POST.get('rejection_reason', 'Not specified')}

I appreciate your consideration and wish you the best in finding the right candidate."""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.job_request.employer,
                    content=reject_message
                )
            
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
            
            # Send completion message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                employer=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                completion_message = f"""✅ **Job Completed!**

The job '{match.job_request.title}' has been marked as completed.

**Rating:** {'⭐' * rating} ({rating}/5)

**Feedback:** {feedback if feedback else 'No feedback provided'}

Thank you for your hard work on this project!

Best regards,
{request.user.get_full_name()}
"""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.worker,
                    content=completion_message
                )
            
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
            
            # Send rating message in chat
            conversation = Conversation.objects.filter(
                job=match.job_request,
                worker=request.user
            ).first()
            
            if conversation:
                from chat.models import Message
                rating_message = f"""⭐ **Employer Rating**

Thank you for the opportunity to work on:

**{match.job_request.title}**

I've rated you {'⭐' * rating} ({rating}/5)

**Feedback:** {feedback if feedback else 'No feedback provided'}

It was a pleasure working with you!

Best regards,
{request.user.get_full_name()}
"""
                
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=match.job_request.employer,
                    content=rating_message
                )
            
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
    
    # Add conversation info for each job
    for job in jobs:
        job.active_conversations = Conversation.objects.filter(
            job=job,
            is_active=True
        ).count()
    
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
    
    # Add conversation info for each application
    for app in applications:
        app.has_conversation = Conversation.objects.filter(
            job=app.job_request,
            worker=request.user
        ).exists()
    
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
        
        # Send notification in all active conversations about job update
        conversations = Conversation.objects.filter(job=job, is_active=True)
        if conversations.exists():
            from chat.models import Message
            update_message = f"""📝 **Job Posting Updated**

The job '{job.title}' has been updated with new information.

Please review the changes and feel free to ask any questions.

[View Job]({request.build_absolute_uri('/jobs/{}/'.format(job.id))})"""
            
            for conversation in conversations:
                receiver = conversation.worker if request.user == conversation.employer else conversation.employer
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=receiver,
                    content=update_message
                )
        
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
        
        # Notify all workers in conversations about cancellation
        conversations = Conversation.objects.filter(job=job, is_active=True)
        if conversations.exists():
            from chat.models import Message
            cancellation_message = f"""❌ **Job Cancelled**

The job '{job.title}' has been cancelled by the employer.

Reason: {request.POST.get('cancellation_reason', 'Not specified')}

We apologize for any inconvenience this may cause.

Thank you for your interest."""
            
            for conversation in conversations:
                receiver = conversation.worker if request.user == conversation.employer else conversation.employer
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    receiver=receiver,
                    content=cancellation_message
                )
        
        messages.success(request, "Job has been cancelled and all applicants have been notified.")
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