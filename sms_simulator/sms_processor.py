from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from jobs.models import JobRequest, JobMatch
from workers.models import Skill, WorkerProfile
from employers.models import EmployerProfile
from accounts.models import Profile
from .utils import send_sms
import random
import string
from django.utils import timezone

def process_sms_command(phone_number, message):
    """
    Main SMS command processor - All actions can be done via SMS
    """
    message = message.strip().upper()
    
    print(f"\nProcessing SMS from {phone_number}: {message}")
    
    # Check if user is registered
    try:
        user = User.objects.get(profile__phone_number=phone_number)
        is_registered = True
    except User.DoesNotExist:
        is_registered = False
    
    # Handle registration first
    if not is_registered and not message.startswith('REGISTER'):
        send_sms(phone_number, "You are not registered. Send: REGISTER [user_type] [username] [password] [location]\n\nExample: REGISTER worker john123 pass123 Nairobi\nOr: REGISTER employer company123 pass123 Nairobi")
        return
    
    # ============ REGISTRATION COMMAND ============
    if message.startswith('REGISTER'):
        parts = message.split()
        if len(parts) >= 5:
            user_type = parts[1].lower()
            username = parts[2]
            password = parts[3]
            location = parts[4]
            company_name = ' '.join(parts[5:]) if len(parts) > 5 else ''
            
            if User.objects.filter(username=username).exists():
                send_sms(phone_number, "Username already taken. Please choose another username.")
                return
            
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=username,
                    last_name=user_type
                )
                
                profile = Profile.objects.create(
                    user=user,
                    phone_number=phone_number,
                    user_type=user_type,
                    location=location
                )
                
                if user_type == 'worker':
                    WorkerProfile.objects.create(user=user)
                    send_sms(phone_number, f"Welcome {username}! You are registered as a WORKER.\n\n"
                           f"Next steps:\n"
                           f"Add skills: ADD_SKILL [skill_name]\n"
                           f"Set available: AVAILABLE\n"
                           f"Find jobs: JOBS\n\n"
                           f"Send HELP for all commands.")
                elif user_type == 'employer':
                    employer_profile = EmployerProfile.objects.create(user=user)
                    if company_name:
                        employer_profile.company_name = company_name
                        employer_profile.save()
                    send_sms(phone_number, f"Welcome {username}! You are registered as an EMPLOYER.\n\n"
                           f"Next steps:\n"
                           f"Post a job: POST|Title|Description|Location|Budget|Skills\n"
                           f"View jobs: MYJOBS\n\n"
                           f"Send HELP for all commands.")
                else:
                    send_sms(phone_number, "Invalid user type. Use 'worker' or 'employer'")
                    user.delete()
                    return
                    
            except Exception as e:
                send_sms(phone_number, f"Registration failed: {str(e)}")
        else:
            send_sms(phone_number, "Invalid REGISTER format.\n\n"
                   "Worker: REGISTER worker username password location\n"
                   "Employer: REGISTER employer username password location company_name")
        return
    
    # ============ HELP COMMAND ============
    if message == 'HELP':
        if user.profile.user_type == 'worker':
            help_text = "WATUKAZI SMS COMMANDS - WORKER\n\n"
            help_text += "REGISTER - Create account\n"
            help_text += "STATUS - View profile\n"
            help_text += "ADD_SKILL [skill] - Add skill\n"
            help_text += "REMOVE_SKILL [skill] - Remove skill\n"
            help_text += "MY_SKILLS - View all skills\n"
            help_text += "JOBS - Find available jobs\n"
            help_text += "APPLY [job_id] - Apply for job\n"
            help_text += "MY_JOBS - View applications\n"
            help_text += "AVAILABLE - Set available\n"
            help_text += "BUSY - Set busy\n"
            help_text += "RATING - View rating\n"
            help_text += "VERIFY - Request verification code\n"
            help_text += "CONFIRM [code] - Verify account\n"
            help_text += "HELP - This menu"
        else:
            help_text = "WATUKAZI SMS COMMANDS - EMPLOYER\n\n"
            help_text += "REGISTER - Create account\n"
            help_text += "STATUS - View profile\n"
            help_text += "POST|Title|Desc|Loc|Budget|Skills - Post job\n"
            help_text += "MYJOBS - View active jobs\n"
            help_text += "JOB [id] - View job details\n"
            help_text += "APPLICANTS [job_id] - View applicants\n"
            help_text += "ACCEPT [match_id] - Accept worker\n"
            help_text += "REJECT [match_id] - Reject worker\n"
            help_text += "COMPLETE [match_id] [rating] - Complete job\n"
            help_text += "HELP - This menu"
        send_sms(phone_number, help_text)
        return
    
    # ============ VERIFICATION COMMANDS ============
    if message == 'VERIFY':
        """Request verification code via SMS"""
        if user.profile.user_type == 'worker':
            try:
                worker = user.worker_profile
                code = ''.join(random.choices(string.digits, k=6))
                worker.verification_code = code
                worker.save()
                send_sms(phone_number, f"Your Watukazi verification code is: {code}\nReply: CONFIRM {code} to verify")
            except Exception as e:
                send_sms(phone_number, "Error requesting verification. Please complete your profile first.")
        else:
            send_sms(phone_number, "Verification is only available for workers at this time.")
        return
    
    if message.startswith('CONFIRM'):
        """Confirm verification via SMS: CONFIRM 123456"""
        parts = message.split()
        if len(parts) >= 2:
            code = parts[1]
            if user.profile.user_type == 'worker':
                worker = user.worker_profile
                if worker.verification_code == code:
                    worker.verification_status = 'verified'
                    worker.verified_at = timezone.now()
                    worker.verification_code = None
                    worker.save()
                    send_sms(phone_number, "Verification successful! Your account is now verified.")
                else:
                    send_sms(phone_number, "Invalid verification code. Please try again.")
            else:
                send_sms(phone_number, "Verification is only available for workers.")
        else:
            send_sms(phone_number, "Usage: CONFIRM [code]")
        return
    
    # ============ WORKER COMMANDS ============
    if user.profile.user_type == 'worker':
        
        # STATUS - View profile
        if message == 'STATUS':
            try:
                worker = WorkerProfile.objects.get(user=user)
                status_text = f"WORKER PROFILE\n"
                status_text += f"Name: {user.username}\n"
                status_text += f"Location: {user.profile.location}\n"
                status_text += f"Status: {worker.get_availability_status_display()}\n"
                status_text += f"Verified: {worker.get_verification_status_display()}\n"
                status_text += f"Skills: {worker.skills.count()}\n"
                status_text += f"Jobs Completed: {worker.total_jobs_completed}\n"
                status_text += f"Rating: {worker.rating}/5"
                send_sms(phone_number, status_text)
            except:
                send_sms(phone_number, "Complete your profile on the website first.")
            return
        
        # ADD_SKILL - Add a skill
        if message.startswith('ADD_SKILL'):
            skill_name = message.replace('ADD_SKILL', '').strip()
            if not skill_name:
                send_sms(phone_number, "Usage: ADD_SKILL [skill_name]\nExample: ADD_SKILL Plumbing")
                return
            
            skills = Skill.objects.filter(name__icontains=skill_name)
            if skills.exists():
                skill = skills.first()
                worker, _ = WorkerProfile.objects.get_or_create(user=user)
                worker.skills.add(skill)
                send_sms(phone_number, f"Added '{skill.name}' to your skills!\nTotal skills: {worker.skills.count()}")
            else:
                all_skills = Skill.objects.all()[:10]
                skill_list = ", ".join([s.name for s in all_skills])
                send_sms(phone_number, f"Skill '{skill_name}' not found.\nAvailable skills: {skill_list}...\nSend HELP for more.")
            return
        
        # REMOVE_SKILL - Remove a skill
        if message.startswith('REMOVE_SKILL'):
            skill_name = message.replace('REMOVE_SKILL', '').strip()
            if not skill_name:
                send_sms(phone_number, "Usage: REMOVE_SKILL [skill_name]")
                return
            
            worker = WorkerProfile.objects.get(user=user)
            skills = worker.skills.filter(name__icontains=skill_name)
            if skills.exists():
                worker.skills.remove(skills.first())
                send_sms(phone_number, f"Removed '{skills.first().name}' from your skills.")
            else:
                send_sms(phone_number, f"Skill '{skill_name}' not in your profile.\nSend MY_SKILLS to see your skills.")
            return
        
        # MY_SKILLS - View all skills
        if message == 'MY_SKILLS':
            worker = WorkerProfile.objects.get(user=user)
            skills = worker.skills.all()
            if skills.exists():
                skill_list = "\n".join([f"- {s.name}" for s in skills])
                send_sms(phone_number, f"YOUR SKILLS ({skills.count()}):\n{skill_list}")
            else:
                send_sms(phone_number, "You have no skills yet.\nSend: ADD_SKILL [skill_name]")
            return
        
        # JOBS - Find available jobs
        if message == 'JOBS':
            jobs = JobRequest.objects.filter(status='open', location__icontains=user.profile.location)[:5]
            if jobs.exists():
                job_text = "AVAILABLE JOBS NEAR YOU:\n\n"
                for job in jobs:
                    job_text += f"ID: {job.id}\n"
                    job_text += f"Title: {job.title}\n"
                    job_text += f"Location: {job.location}\n"
                    job_text += f"Budget: KES {job.budget if job.budget else 'Negotiable'}\n"
                    job_text += f"To apply: APPLY {job.id}\n"
                    job_text += "-" * 20 + "\n"
                send_sms(phone_number, job_text)
            else:
                send_sms(phone_number, "No jobs available in your area.\nCheck back later or update your location!")
            return
        
        # APPLY - Apply for a job
        if message.startswith('APPLY'):
            parts = message.split()
            if len(parts) >= 2:
                try:
                    job_id = int(parts[1])
                    job = JobRequest.objects.get(id=job_id, status='open')
                    
                    if JobMatch.objects.filter(job_request=job, worker=user).exists():
                        send_sms(phone_number, f"You have already applied for '{job.title}'")
                        return
                    
                    match = JobMatch.objects.create(
                        job_request=job,
                        worker=user,
                        status='pending',
                        match_score=75
                    )
                    
                    send_sms(phone_number, f"Applied for '{job.title}'!\n"
                           f"Employer: {job.employer.username}\n"
                           f"Contact: {job.employer.profile.phone_number}\n"
                           f"They will contact you soon.")
                    
                    employer_msg = f"New application!\n"
                    employer_msg += f"Job: {job.title}\n"
                    employer_msg += f"Worker: {user.username}\n"
                    employer_msg += f"Contact: {phone_number}\n"
                    employer_msg += f"Reply: APPLICANTS {job.id} to view all"
                    send_sms(job.employer.profile.phone_number, employer_msg)
                    
                except (ValueError, JobRequest.DoesNotExist):
                    send_sms(phone_number, "Invalid job ID. Use JOBS to see available jobs.")
            else:
                send_sms(phone_number, "Usage: APPLY [job_id]\nExample: APPLY 5")
            return
        
        # MY_JOBS - View applications
        if message == 'MY_JOBS':
            applications = JobMatch.objects.filter(worker=user).order_by('-created_at')[:5]
            if applications.exists():
                text = "YOUR JOB APPLICATIONS:\n\n"
                for app in applications:
                    text += f"Job: {app.job_request.title}\n"
                    text += f"Status: {app.get_status_display()}\n"
                    text += f"Employer: {app.job_request.employer.username}\n"
                    if app.status == 'accepted':
                        text += f"Contact: {app.job_request.employer.profile.phone_number}\n"
                    text += "\n"
                send_sms(phone_number, text)
            else:
                send_sms(phone_number, "You haven't applied for any jobs yet.\nUse JOBS to find jobs!")
            return
        
        # AVAILABLE - Set available status
        if message == 'AVAILABLE':
            worker = WorkerProfile.objects.get(user=user)
            worker.availability_status = 'available'
            worker.save()
            send_sms(phone_number, "Status: AVAILABLE\nYou will now receive job alerts!")
            return
        
        # BUSY - Set busy status
        if message == 'BUSY':
            worker = WorkerProfile.objects.get(user=user)
            worker.availability_status = 'busy'
            worker.save()
            send_sms(phone_number, "Status: BUSY\nYou won't receive job alerts until you set AVAILABLE.")
            return
        
        # RATING - View rating
        if message == 'RATING':
            worker = WorkerProfile.objects.get(user=user)
            rating_text = f"YOUR RATING: {worker.rating}/5\n"
            rating_text += f"Jobs Completed: {worker.total_jobs_completed}\n"
            if worker.rating >= 4:
                rating_text += "Excellent! Keep up the great work!"
            elif worker.rating >= 3:
                rating_text += "Good! You're doing well!"
            elif worker.rating > 0:
                rating_text += "Keep improving!"
            else:
                rating_text += "Complete jobs to get ratings!"
            send_sms(phone_number, rating_text)
            return
    
    # ============ EMPLOYER COMMANDS ============
    elif user.profile.user_type == 'employer':
        
        # STATUS - View profile
        if message == 'STATUS':
            employer = EmployerProfile.objects.get(user=user)
            jobs_count = JobRequest.objects.filter(employer=user).count()
            active_jobs = JobRequest.objects.filter(employer=user, status='open').count()
            send_sms(phone_number, f"EMPLOYER PROFILE\n"
                   f"Name: {user.username}\n"
                   f"Company: {employer.company_name or 'Not set'}\n"
                   f"Location: {user.profile.location}\n"
                   f"Total Jobs: {jobs_count}\n"
                   f"Active Jobs: {active_jobs}\n"
                   f"Rating: {employer.rating}/5")
            return
        
        # POST - Post a job via SMS
        if message.startswith('POST|'):
            parts = message.split('|')
            if len(parts) >= 4:
                try:
                    title = parts[1] if len(parts) > 1 else "New Job"
                    description = parts[2] if len(parts) > 2 else "Job posted via SMS"
                    location = parts[3] if len(parts) > 3 else user.profile.location
                    budget = parts[4] if len(parts) > 4 else None
                    skill_names = parts[5].split(',') if len(parts) > 5 else []
                    
                    job = JobRequest.objects.create(
                        employer=user,
                        title=title,
                        description=description,
                        location=location,
                        budget=budget,
                        status='open'
                    )
                    
                    for skill_name in skill_names:
                        try:
                            skill = Skill.objects.get(name__iexact=skill_name.strip())
                            job.required_skills.add(skill)
                        except Skill.DoesNotExist:
                            pass
                    
                    send_sms(phone_number, f"Job posted successfully!\n"
                           f"ID: {job.id}\n"
                           f"Title: {job.title}\n"
                           f"Location: {job.location}\n\n"
                           f"Workers will be notified automatically!")
                    
                    matches = job.auto_match_workers()
                    if matches:
                        send_sms(phone_number, f"{len(matches)} workers have been notified about this job.")
                    
                except Exception as e:
                    send_sms(phone_number, f"Error posting job: {str(e)}")
            else:
                send_sms(phone_number, "Invalid POST format.\n"
                       "Format: POST|Title|Description|Location|Budget|Skill1,Skill2\n"
                       "Example: POST|Need Plumber|Fix bathroom leak|Nairobi|5000|Plumbing")
            return
        
        # MYJOBS - View active jobs
        if message == 'MYJOBS':
            jobs = JobRequest.objects.filter(employer=user, status='open')
            if jobs.exists():
                text = "YOUR ACTIVE JOBS:\n\n"
                for job in jobs:
                    text += f"ID: {job.id}\n"
                    text += f"Title: {job.title}\n"
                    text += f"Location: {job.location}\n"
                    text += f"Budget: KES {job.budget if job.budget else 'Negotiable'}\n"
                    text += f"Applicants: {job.matches.count()}\n"
                    text += f"To view details: JOB {job.id}\n"
                    text += "-" * 20 + "\n"
                send_sms(phone_number, text)
            else:
                send_sms(phone_number, "No active jobs.\nPost a job: POST|Title|Description|Location|Budget|Skills")
            return
        
        # JOB - View job details
        if message.startswith('JOB'):
            parts = message.split()
            if len(parts) >= 2:
                try:
                    job_id = int(parts[1])
                    job = JobRequest.objects.get(id=job_id, employer=user)
                    text = f"JOB DETAILS\n"
                    text += f"ID: {job.id}\n"
                    text += f"Title: {job.title}\n"
                    text += f"Description: {job.description[:100]}...\n"
                    text += f"Location: {job.location}\n"
                    text += f"Budget: KES {job.budget if job.budget else 'Negotiable'}\n"
                    text += f"Status: {job.get_status_display()}\n"
                    text += f"Applicants: {job.matches.count()}\n"
                    text += f"To view applicants: APPLICANTS {job.id}"
                    send_sms(phone_number, text)
                except (ValueError, JobRequest.DoesNotExist):
                    send_sms(phone_number, "Invalid job ID. Use MYJOBS to see your jobs.")
            else:
                send_sms(phone_number, "Usage: JOB [job_id]")
            return
        
        # APPLICANTS - View applicants for a job
        if message.startswith('APPLICANTS'):
            parts = message.split()
            if len(parts) >= 2:
                try:
                    job_id = int(parts[1])
                    job = JobRequest.objects.get(id=job_id, employer=user)
                    applicants = job.matches.filter(status='pending')
                    
                    if applicants.exists():
                        text = f"APPLICANTS FOR '{job.title}':\n\n"
                        for app in applicants[:5]:
                            text += f"ID: {app.id}\n"
                            text += f"Name: {app.worker.username}\n"
                            text += f"Phone: {app.worker.profile.phone_number}\n"
                            text += f"Match: {app.match_score}%\n"
                            text += f"To accept: ACCEPT {app.id}\n"
                            text += f"To reject: REJECT {app.id}\n"
                            text += "-" * 20 + "\n"
                        send_sms(phone_number, text)
                    else:
                        send_sms(phone_number, f"No applicants for job '{job.title}' yet.")
                except (ValueError, JobRequest.DoesNotExist):
                    send_sms(phone_number, "Invalid job ID. Use MYJOBS to see your jobs.")
            else:
                send_sms(phone_number, "Usage: APPLICANTS [job_id]")
            return
        
        # ACCEPT - Accept an applicant
        if message.startswith('ACCEPT'):
            parts = message.split()
            if len(parts) >= 2:
                try:
                    match_id = int(parts[1])
                    match = JobMatch.objects.get(id=match_id, job_request__employer=user)
                    match.status = 'accepted'
                    match.save()
                    
                    match.job_request.status = 'matched'
                    match.job_request.save()
                    
                    send_sms(phone_number, f"Accepted {match.worker.username} for '{match.job_request.title}'\n"
                           f"Worker contact: {match.worker.profile.phone_number}")
                    
                    send_sms(match.worker.profile.phone_number, f"Great news! {user.username} has accepted your application for '{match.job_request.title}'.\n"
                           f"Contact employer: {phone_number}\n"
                           f"Good luck with the job!")
                    
                except (ValueError, JobMatch.DoesNotExist):
                    send_sms(phone_number, "Invalid applicant ID. Use APPLICANTS [job_id] to see IDs.")
            else:
                send_sms(phone_number, "Usage: ACCEPT [applicant_id]")
            return
        
        # REJECT - Reject an applicant
        if message.startswith('REJECT'):
            parts = message.split()
            if len(parts) >= 2:
                try:
                    match_id = int(parts[1])
                    match = JobMatch.objects.get(id=match_id, job_request__employer=user)
                    match.status = 'rejected'
                    match.save()
                    
                    send_sms(phone_number, f"Rejected {match.worker.username} for '{match.job_request.title}'")
                    
                    send_sms(match.worker.profile.phone_number, f"Thank you for your interest in '{match.job_request.title}'. The employer has selected another candidate.")
                    
                except (ValueError, JobMatch.DoesNotExist):
                    send_sms(phone_number, "Invalid applicant ID. Use APPLICANTS [job_id] to see IDs.")
            else:
                send_sms(phone_number, "Usage: REJECT [applicant_id]")
            return
        
        # COMPLETE - Complete a job and rate worker
        if message.startswith('COMPLETE'):
            parts = message.split()
            if len(parts) >= 3:
                try:
                    match_id = int(parts[1])
                    rating = int(parts[2])
                    match = JobMatch.objects.get(id=match_id, job_request__employer=user)
                    
                    if 1 <= rating <= 5:
                        match.complete_job(rating=rating)
                        send_sms(phone_number, f"Job completed! You rated {match.worker.username} {rating}/5 stars.")
                        
                        send_sms(match.worker.profile.phone_number, f"Job completed!\n"
                               f"Employer rated you {rating}/5 stars.\n"
                               f"Thank you for your hard work!")
                    else:
                        send_sms(phone_number, "Rating must be between 1 and 5")
                except (ValueError, JobMatch.DoesNotExist):
                    send_sms(phone_number, "Invalid match ID. Use APPLICANTS [job_id] to see IDs.")
            else:
                send_sms(phone_number, "Usage: COMPLETE [match_id] [rating]\nExample: COMPLETE 5 4")
            return
    
    # Unknown command
    else:
        send_sms(phone_number, "Command not recognized.\nSend HELP for available commands.")