"""
SMS Command Processor for Watukazi System
Handles incoming SMS commands and routes them to appropriate handlers
"""

import re
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import send_sms
from jobs.models import JobRequest, JobMatch
from workers.models import Skill, WorkerProfile

def process_sms_command(phone_number, message):
    """
    Main entry point for processing SMS commands
    """
    message = message.strip().upper()
    
    # Parse command
    parts = message.split()
    command = parts[0] if parts else ''
    
    # Find user by phone number
    try:
        user = User.objects.get(profile__phone_number=phone_number)
    except User.DoesNotExist:
        # New user - only allow REGISTER command
        if command == 'REGISTER' and len(parts) >= 4:
            return handle_register(phone_number, parts)
        else:
            response = "You are not registered. Send: REGISTER [worker/employer] [username] [password] [location]"
            send_sms(phone_number, response)
            return response
    
    # Route commands based on user type
    user_type = user.profile.user_type
    
    # Common commands for all users
    if command == 'HELP':
        return handle_help(phone_number, user_type)
    elif command == 'STATUS':
        return handle_status(phone_number, user)
    elif command == 'CONFIRM':
        return handle_confirm(phone_number, user, parts)
    elif command == 'CANCEL':
        return handle_cancel(phone_number, user, parts)
    
    # Worker-specific commands
    if user_type == 'worker':
        if command == 'JOBS':
            return handle_worker_jobs(phone_number, user)
        elif command == 'APPLY':
            return handle_worker_apply(phone_number, user, parts)
        elif command == 'MY_JOBS':
            return handle_worker_my_jobs(phone_number, user)
        elif command == 'ADD_SKILL':
            return handle_worker_add_skill(phone_number, user, parts)
        elif command == 'AVAILABLE':
            return handle_worker_available(phone_number, user)
        elif command == 'MY_SKILLS':
            return handle_worker_my_skills(phone_number, user)
        elif command == 'COMPLETE':
            return handle_worker_complete(phone_number, user, parts)
    
    # Employer-specific commands
    elif user_type == 'employer':
        if command == 'POST':
            return handle_employer_post(phone_number, user, message)
        elif command == 'MYJOBS':
            return handle_employer_my_jobs(phone_number, user)
        elif command == 'APPLICANTS':
            return handle_employer_applicants(phone_number, user, parts)
        elif command == 'ACCEPT':
            return handle_employer_accept(phone_number, user, parts)
        elif command == 'REJECT':
            return handle_employer_reject(phone_number, user, parts)
        elif command == 'COMPLETE':
            return handle_employer_complete(phone_number, user, parts)
    
    # Admin commands
    elif user_type == 'admin':
        if command == 'ADMIN':
            return handle_admin(phone_number, user, parts)
    
    # Default response
    response = "Unknown command. Send HELP for available commands."
    send_sms(phone_number, response)
    return response


def handle_register(phone_number, parts):
    """Handle user registration"""
    if len(parts) < 5:
        response = "Usage: REGISTER [worker/employer] [username] [password] [location]"
        send_sms(phone_number, response)
        return response
    
    user_type = parts[1].lower()
    username = parts[2]
    password = parts[3]
    location = ' '.join(parts[4:])
    
    # Check if username exists
    if User.objects.filter(username=username).exists():
        response = f"Username '{username}' already exists. Please choose another."
        send_sms(phone_number, response)
        return response
    
    # Create user
    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=username
        )
        
        # Create profile
        from accounts.models import Profile
        profile = Profile.objects.create(
            user=user,
            user_type=user_type,
            phone_number=phone_number,
            location=location,
            is_verified=True
        )
        
        # Create specific profile
        if user_type == 'worker':
            WorkerProfile.objects.create(user=user, availability_status='available')
            response = f"Worker account created! Username: {username}. Send JOBS to find work."
        elif user_type == 'employer':
            from employers.models import EmployerProfile
            EmployerProfile.objects.create(user=user, company_name=username)
            response = f"Employer account created! Username: {username}. Send POST to create a job."
        else:
            response = "Invalid user type. Use 'worker' or 'employer'."
        
        send_sms(phone_number, response)
        return response
        
    except Exception as e:
        response = f"Registration failed: {str(e)}"
        send_sms(phone_number, response)
        return response


def handle_help(phone_number, user_type):
    """Send help menu"""
    if user_type == 'worker':
        help_text = """WATUKAZI WORKER COMMANDS:

JOBS - Find available jobs
APPLY [job_id] - Apply for a job
MY_JOBS - View your applications
ADD_SKILL [skill] - Add a skill to your profile
MY_SKILLS - View your skills
AVAILABLE - Mark yourself available for work
CONFIRM [match_id] - Confirm an accepted job
CANCEL [match_id] - Cancel a job
COMPLETE [match_id] [rating] - Complete job
STATUS - View your profile
HELP - Show this menu"""
    
    elif user_type == 'employer':
        help_text = """WATUKAZI EMPLOYER COMMANDS:

POST|Title|Desc|Location|Budget|Skills - Post a job
MYJOBS - View your active jobs
APPLICANTS [job_id] - View applicants for job
ACCEPT [match_id] - Accept a worker
REJECT [match_id] - Reject a worker
CONFIRM [match_id] - Confirm worker acceptance
COMPLETE [match_id] [rating] - Complete job
STATUS - View your profile
HELP - Show this menu"""
    
    else:
        help_text = """WATUKAZI COMMANDS:

REGISTER [worker/employer] [username] [password] [location] - Create account
STATUS - View your profile
HELP - Show this menu"""
    
    send_sms(phone_number, help_text)
    return help_text


def handle_status(phone_number, user):
    """Show user status"""
    profile = user.profile
    
    if profile.user_type == 'worker':
        worker_profile = user.worker_profile
        accepted_count = JobMatch.objects.filter(worker=user, status='accepted').count()
        completed_count = JobMatch.objects.filter(worker=user, status='completed').count()
        
        status_text = f"""Your Profile:
Name: {user.get_full_name() or user.username}
Type: Worker
Location: {profile.location}
Rating: {worker_profile.rating}/5
Jobs Completed: {worker_profile.total_jobs_completed}
Status: {worker_profile.get_availability_status_display()}
Pending Acceptances: {accepted_count}
Skills: {', '.join([s.name for s in worker_profile.skills.all()[:5]])}"""
    
    elif profile.user_type == 'employer':
        from employers.models import EmployerProfile
        employer_profile = EmployerProfile.objects.get(user=user)
        active_jobs = JobRequest.objects.filter(employer=user, status='open').count()
        
        status_text = f"""Your Profile:
Name: {user.get_full_name() or user.username}
Company: {employer_profile.company_name or 'Not set'}
Type: Employer
Location: {profile.location}
Active Jobs: {active_jobs}
Total Applications: {JobMatch.objects.filter(job_request__employer=user).count()}"""
    
    else:
        status_text = f"""Admin Account:
Username: {user.username}
Email: {user.email}
Type: Administrator"""
    
    send_sms(phone_number, status_text)
    return status_text


def handle_worker_jobs(phone_number, user):
    """List available jobs for workers"""
    # Get jobs matching worker's skills and location
    worker_skills = user.worker_profile.skills.all()
    worker_location = user.profile.location
    
    jobs = JobRequest.objects.filter(status='open')
    
    if worker_skills.exists():
        jobs = jobs.filter(required_skills__in=worker_skills).distinct()
    
    if worker_location:
        jobs = jobs.filter(location__icontains=worker_location)
    
    jobs = jobs.order_by('-created_at')[:10]
    
    if not jobs:
        response = "No jobs available. Check back later!"
    else:
        response = f"📋 AVAILABLE JOBS (Top {jobs.count()}):\n\n"
        for i, job in enumerate(jobs, 1):
            response += f"{i}. {job.title}\n"
            response += f"   ID:{job.id} | {job.location}\n"
            response += f"   KES {job.budget if job.budget else 'Negotiable'}\n"
            response += f"   Reply: APPLY {job.id}\n\n"
    
    send_sms(phone_number, response)
    return response


def handle_worker_apply(phone_number, user, parts):
    """Worker applies for a job"""
    if len(parts) < 2:
        response = "Usage: APPLY [job_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        job_id = int(parts[1])
        job = JobRequest.objects.get(id=job_id, status='open')
        
        # Check if already applied
        if JobMatch.objects.filter(job_request=job, worker=user).exists():
            response = f"You have already applied for '{job.title}'"
            send_sms(phone_number, response)
            return response
        
        # Create application
        match = JobMatch.objects.create(
            job_request=job,
            worker=user,
            status='pending',
            match_score=50
        )
        
        response = f"✅ Applied for '{job.title}'! The employer will review your application and contact you."
        send_sms(phone_number, response)
        
        # Notify employer
        employer_msg = f"📝 New application!\nWorker: {user.get_full_name() or user.username}\nJob: {job.title}\nMatch Score: 50%\nLogin to review: http://127.0.0.1:8000/jobs/{job.id}/"
        send_sms(job.employer.profile.phone_number, employer_msg)
        
        return response
        
    except JobRequest.DoesNotExist:
        response = f"Job #{parts[1]} not found or no longer available."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid job ID. Use: APPLY [job_id]"
        send_sms(phone_number, response)
        return response


def handle_worker_my_jobs(phone_number, user):
    """Show worker's applications"""
    applications = JobMatch.objects.filter(worker=user).order_by('-created_at')[:10]
    
    if not applications:
        response = "You haven't applied for any jobs yet. Send JOBS to find work."
    else:
        response = "📋 YOUR APPLICATIONS:\n\n"
        for app in applications:
            status_emoji = "⏳" if app.status == 'pending' else "✅" if app.status == 'accepted' else "❌" if app.status == 'rejected' else "🎉" if app.status == 'completed' else "⚠️"
            response += f"{status_emoji} {app.job_request.title}\n"
            response += f"   Status: {app.get_status_display()}\n"
            
            if app.status == 'accepted':
                if app.response_deadline:
                    deadline = app.response_deadline.strftime('%Y-%m-%d %H:%M')
                    response += f"   Confirm before: {deadline}\n"
                response += f"   Reply: CONFIRM {app.id} to accept\n"
            
            response += "\n"
    
    send_sms(phone_number, response)
    return response


def handle_worker_add_skill(phone_number, user, parts):
    """Add skill to worker profile"""
    if len(parts) < 2:
        response = "Usage: ADD_SKILL [skill_name]"
        send_sms(phone_number, response)
        return response
    
    skill_name = ' '.join(parts[1:]).title()
    
    try:
        skill, created = Skill.objects.get_or_create(name=skill_name)
        user.worker_profile.skills.add(skill)
        
        response = f"✅ Added skill: {skill_name}\nYour skills: {', '.join([s.name for s in user.worker_profile.skills.all()])}"
        send_sms(phone_number, response)
        return response
        
    except Exception as e:
        response = f"Failed to add skill: {str(e)}"
        send_sms(phone_number, response)
        return response


def handle_worker_my_skills(phone_number, user):
    """Show worker's skills"""
    skills = user.worker_profile.skills.all()
    
    if skills:
        response = f"Your Skills:\n{', '.join([s.name for s in skills])}"
    else:
        response = "You have no skills. Send ADD_SKILL [skill_name] to add skills."
    
    send_sms(phone_number, response)
    return response


def handle_worker_available(phone_number, user):
    """Mark worker as available"""
    user.worker_profile.availability_status = 'available'
    user.worker_profile.save()
    
    response = "✅ You are now marked as AVAILABLE for work. Employers can now find you."
    send_sms(phone_number, response)
    return response


def handle_confirm(phone_number, user, parts):
    """Confirm an accepted job"""
    if len(parts) < 2:
        response = "Usage: CONFIRM [match_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        match = JobMatch.objects.get(id=match_id)
        
        # Check permissions
        if user.profile.user_type == 'worker' and match.worker != user:
            response = "You don't have permission to confirm this job."
            send_sms(phone_number, response)
            return response
        elif user.profile.user_type == 'employer' and match.job_request.employer != user:
            response = "You don't have permission to confirm this job."
            send_sms(phone_number, response)
            return response
        
        if match.status == 'accepted':
            match.status = 'confirmed'
            match.save()
            
            # Send confirmation to the other party
            if user.profile.user_type == 'worker':
                # Notify employer
                employer_msg = f"✅ Worker {match.worker.get_full_name() or match.worker.username} has confirmed job '{match.job_request.title}'."
                send_sms(match.job_request.employer.profile.phone_number, employer_msg)
                
                response = f"✅ Job confirmed! You have confirmed '{match.job_request.title}'. Please report as directed."
            else:
                # Notify worker
                worker_msg = f"✅ Employer has confirmed your application for '{match.job_request.title}'. Please report as directed."
                send_sms(match.worker.profile.phone_number, worker_msg)
                
                response = f"✅ Worker confirmed! {match.worker.get_full_name() or match.worker.username} has confirmed the job."
            
            send_sms(phone_number, response)
            return response
        else:
            response = f"Job is not in accepted status. Current status: {match.get_status_display()}"
            send_sms(phone_number, response)
            return response
            
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID. Use: CONFIRM [match_id]"
        send_sms(phone_number, response)
        return response


def handle_cancel(phone_number, user, parts):
    """Cancel a job or application"""
    if len(parts) < 2:
        response = "Usage: CANCEL [match_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        match = JobMatch.objects.get(id=match_id)
        
        # Check permissions
        if user.profile.user_type == 'worker' and match.worker != user:
            response = "You don't have permission to cancel this job."
            send_sms(phone_number, response)
            return response
        elif user.profile.user_type == 'employer' and match.job_request.employer != user:
            response = "You don't have permission to cancel this job."
            send_sms(phone_number, response)
            return response
        
        if match.status in ['pending', 'accepted']:
            match.status = 'cancelled'
            match.save()
            
            # Notify the other party
            if user.profile.user_type == 'worker':
                employer_msg = f"Worker {match.worker.get_full_name() or match.worker.username} has cancelled job '{match.job_request.title}'."
                send_sms(match.job_request.employer.profile.phone_number, employer_msg)
                response = f"✅ Cancelled job '{match.job_request.title}'."
            else:
                worker_msg = f"Employer has cancelled job '{match.job_request.title}'."
                send_sms(match.worker.profile.phone_number, worker_msg)
                response = f"✅ Cancelled application for '{match.job_request.title}'."
            
            send_sms(phone_number, response)
            return response
        else:
            response = f"Cannot cancel job in {match.get_status_display()} status."
            send_sms(phone_number, response)
            return response
            
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID. Use: CANCEL [match_id]"
        send_sms(phone_number, response)
        return response


def handle_employer_post(phone_number, user, message):
    """Post a job via SMS"""
    # Parse pipe-separated format: POST|Title|Description|Location|Budget|Skills
    try:
        parts = message.split('|')
        if len(parts) < 6:
            response = "Usage: POST|Title|Description|Location|Budget|Skill1,Skill2,Skill3"
            send_sms(phone_number, response)
            return response
        
        title = parts[1].strip()
        description = parts[2].strip()
        location = parts[3].strip()
        budget = parts[4].strip() if parts[4].strip() else None
        skill_names = [s.strip() for s in parts[5].split(',')]
        
        # Create job
        job = JobRequest.objects.create(
            employer=user,
            title=title,
            description=description,
            location=location,
            budget=budget if budget else None,
            duration_days=1
        )
        
        # Add skills
        for skill_name in skill_names:
            if skill_name:
                skill, created = Skill.objects.get_or_create(name=skill_name.title())
                job.required_skills.add(skill)
        
        # Auto-match workers
        matches_created = job.auto_match_workers()
        
        response = f"✅ Job posted!\nID: {job.id}\nTitle: {job.title}\nLocation: {job.location}\nSkills: {', '.join(skill_names)}\n\n"
        
        if matches_created:
            response += f"🚀 {len(matches_created)} matching workers have been notified."
        else:
            response += "⚠️ No matching workers found at the moment."
        
        send_sms(phone_number, response)
        return response
        
    except Exception as e:
        response = f"Failed to post job: {str(e)}"
        send_sms(phone_number, response)
        return response


def handle_employer_my_jobs(phone_number, user):
    """Show employer's jobs"""
    jobs = JobRequest.objects.filter(employer=user).order_by('-created_at')[:10]
    
    if not jobs:
        response = "You haven't posted any jobs. Send POST to create a job."
    else:
        response = "📋 YOUR JOBS:\n\n"
        for job in jobs:
            applications = JobMatch.objects.filter(job_request=job, status='pending').count()
            response += f"ID:{job.id} | {job.title}\n"
            response += f"   Status: {job.get_status_display()}\n"
            response += f"   Applicants: {job.matches.count()} (Pending: {applications})\n"
            response += f"   Reply: APPLICANTS {job.id}\n\n"
    
    send_sms(phone_number, response)
    return response


def handle_employer_applicants(phone_number, user, parts):
    """Show applicants for a job"""
    if len(parts) < 2:
        response = "Usage: APPLICANTS [job_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        job_id = int(parts[1])
        job = JobRequest.objects.get(id=job_id, employer=user)
        
        applicants = JobMatch.objects.filter(job_request=job).order_by('-match_score')
        
        if not applicants:
            response = f"No applicants for '{job.title}' yet."
        else:
            response = f"📋 APPLICANTS for '{job.title}':\n\n"
            for i, app in enumerate(applicants[:10], 1):
                response += f"{i}. {app.worker.get_full_name() or app.worker.username}\n"
                response += f"   ID:{app.id} | Match: {app.match_score}%\n"
                response += f"   Phone: {app.worker.profile.phone_number}\n"
                response += f"   Reply: ACCEPT {app.id} or REJECT {app.id}\n\n"
        
        send_sms(phone_number, response)
        return response
        
    except JobRequest.DoesNotExist:
        response = f"Job #{parts[1]} not found or you don't own it."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid job ID. Use: APPLICANTS [job_id]"
        send_sms(phone_number, response)
        return response


def handle_employer_accept(phone_number, user, parts):
    """Accept a worker application"""
    if len(parts) < 2:
        response = "Usage: ACCEPT [match_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        match = JobMatch.objects.get(id=match_id, job_request__employer=user)
        
        if match.status == 'pending':
            match.status = 'accepted'
            match.save()
            
            # Send approval message to worker
            worker_msg = f"✅ Congratulations! Your application for '{match.job_request.title}' has been accepted!\n"
            worker_msg += f"Contact employer: {match.job_request.employer.profile.phone_number}\n"
            worker_msg += f"Reply CONFIRM {match.id} to accept the job."
            send_sms(match.worker.profile.phone_number, worker_msg)
            
            response = f"✅ Accepted {match.worker.get_full_name() or match.worker.username} for '{match.job_request.title}'.\nWorker will be notified."
            
        else:
            response = f"Cannot accept application in {match.get_status_display()} status."
        
        send_sms(phone_number, response)
        return response
        
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID. Use: ACCEPT [match_id]"
        send_sms(phone_number, response)
        return response


def handle_employer_reject(phone_number, user, parts):
    """Reject a worker application"""
    if len(parts) < 2:
        response = "Usage: REJECT [match_id]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        match = JobMatch.objects.get(id=match_id, job_request__employer=user)
        
        if match.status == 'pending':
            match.status = 'rejected'
            match.save()
            
            # Send rejection message to worker
            worker_msg = f"Thank you for your interest in '{match.job_request.title}'. The employer has selected another candidate."
            send_sms(match.worker.profile.phone_number, worker_msg)
            
            response = f"❌ Rejected {match.worker.get_full_name() or match.worker.username} for '{match.job_request.title}'."
            
        else:
            response = f"Cannot reject application in {match.get_status_display()} status."
        
        send_sms(phone_number, response)
        return response
        
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID. Use: REJECT [match_id]"
        send_sms(phone_number, response)
        return response


def handle_worker_complete(phone_number, user, parts):
    """Worker marks job as completed and rates employer"""
    if len(parts) < 3:
        response = "Usage: COMPLETE [match_id] [rating] (1-5)\nOptionally add feedback: COMPLETE [match_id] [rating] [feedback]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        rating = int(parts[2])
        
        if rating < 1 or rating > 5:
            response = "Rating must be between 1 and 5."
            send_sms(phone_number, response)
            return response
        
        match = JobMatch.objects.get(id=match_id, worker=user)
        
        if match.status == 'confirmed':
            feedback = ' '.join(parts[3:]) if len(parts) > 3 else ''
            match.rate_employer(rating=rating, feedback=feedback)
            
            # Notify employer
            employer_msg = f"Worker {user.get_full_name() or user.username} has completed job '{match.job_request.title}' and rated you {rating}/5 stars."
            send_sms(match.job_request.employer.profile.phone_number, employer_msg)
            
            response = f"✅ Job completed! You rated employer {rating}/5 stars. Thank you!"
            
        else:
            response = f"Cannot complete job in {match.get_status_display()} status."
        
        send_sms(phone_number, response)
        return response
        
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID or rating. Use: COMPLETE [match_id] [rating]"
        send_sms(phone_number, response)
        return response


def handle_employer_complete(phone_number, user, parts):
    """Employer marks job as completed and rates worker"""
    if len(parts) < 3:
        response = "Usage: COMPLETE [match_id] [rating] (1-5)\nOptionally add feedback: COMPLETE [match_id] [rating] [feedback]"
        send_sms(phone_number, response)
        return response
    
    try:
        match_id = int(parts[1])
        rating = int(parts[2])
        
        if rating < 1 or rating > 5:
            response = "Rating must be between 1 and 5."
            send_sms(phone_number, response)
            return response
        
        match = JobMatch.objects.get(id=match_id, job_request__employer=user)
        
        if match.status == 'confirmed':
            feedback = ' '.join(parts[3:]) if len(parts) > 3 else ''
            match.complete_job(rating=rating, feedback=feedback)
            
            # Notify worker
            worker_msg = f"Employer has completed job '{match.job_request.title}' and rated you {rating}/5 stars.\n"
            if feedback:
                worker_msg += f"Feedback: {feedback}\n"
            worker_msg += "Thank you for your hard work!"
            send_sms(match.worker.profile.phone_number, worker_msg)
            
            response = f"✅ Job completed! You rated worker {rating}/5 stars."
            
        else:
            response = f"Cannot complete job in {match.get_status_display()} status."
        
        send_sms(phone_number, response)
        return response
        
    except JobMatch.DoesNotExist:
        response = f"Match #{parts[1]} not found."
        send_sms(phone_number, response)
        return response
    except ValueError:
        response = "Invalid match ID or rating. Use: COMPLETE [match_id] [rating]"
        send_sms(phone_number, response)
        return response


def handle_admin(phone_number, user, parts):
    """Admin commands"""
    if not user.is_superuser:
        response = "Admin access required."
        send_sms(phone_number, response)
        return response
    
    if len(parts) < 2:
        response = "Admin commands:\nADMIN STATS - System statistics\nADMIN USERS - User count"
        send_sms(phone_number, response)
        return response
    
    subcommand = parts[1].upper()
    
    if subcommand == 'STATS':
        total_users = User.objects.count()
        workers = User.objects.filter(profile__user_type='worker').count()
        employers = User.objects.filter(profile__user_type='employer').count()
        jobs = JobRequest.objects.count()
        matches = JobMatch.objects.count()
        
        response = f"📊 SYSTEM STATISTICS:\n\nTotal Users: {total_users}\nWorkers: {workers}\nEmployers: {employers}\nJobs Posted: {jobs}\nApplications: {matches}"
        
    elif subcommand == 'USERS':
        users = User.objects.all().order_by('-date_joined')[:20]
        response = "📋 RECENT USERS:\n\n"
        for u in users:
            response += f"{u.username} ({u.profile.user_type})\n"
            response += f"   Joined: {u.date_joined.strftime('%Y-%m-%d')}\n\n"
    
    else:
        response = f"Unknown admin command: {subcommand}"
    
    send_sms(phone_number, response)
    return response