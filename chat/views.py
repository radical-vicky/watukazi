from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from .models import Conversation, Message, MessageAttachment
from jobs.models import JobRequest, JobMatch
from accounts.models import Profile

@login_required
def conversations_list(request):
    """List all conversations for the current user"""
    user = request.user
    
    # Get all conversations where user is either employer or worker
    conversations = Conversation.objects.filter(
        Q(employer=user) | Q(worker=user),
        is_active=True
    ).annotate(
        unread_count=Count('messages', filter=Q(
            messages__is_read=False,
            messages__is_deleted=False
        ) & ~Q(messages__sender=user))
    )
    
    # Add last message to each conversation
    for conv in conversations:
        conv.last_message = conv.get_last_message()
    
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'conversations': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'chat/conversations_list.html', context)

@login_required
def conversation_detail(request, conversation_id):
    """View a specific conversation"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id,
        is_active=True
    )
    
    # Check if user is part of this conversation
    if request.user not in [conversation.employer, conversation.worker]:
        raise PermissionDenied("You don't have permission to view this conversation.")
    
    # Mark messages as read
    conversation.mark_as_read(request.user)
    
    # Get all messages (not paginated for simplicity)
    messages_qs = conversation.messages.filter(is_deleted=False).select_related('sender', 'receiver')
    
    # Debug: Print message count
    print(f"Conversation {conversation_id} has {messages_qs.count()} messages")
    for msg in messages_qs:
        print(f"  - {msg.sender.username}: {msg.content[:50]}")
    
    # Get job and match info
    job = conversation.job
    is_employer = request.user == conversation.employer
    other_user = conversation.worker if is_employer else conversation.employer
    
    # Get other user's profile
    other_profile = Profile.objects.get(user=other_user)
    
    context = {
        'conversation': conversation,
        'messages': messages_qs,  # Pass all messages
        'job': job,
        'is_employer': is_employer,
        'other_user': other_user,
        'other_profile': other_profile,
    }
    return render(request, 'chat/conversation_detail.html', context)


@login_required
@require_http_methods(["POST"])
def send_message(request, conversation_id):
    """Send a new message in a conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, is_active=True)
    
    # Check permission
    if request.user not in [conversation.employer, conversation.worker]:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Message content is required'}, status=400)
    
    # Determine receiver
    receiver = conversation.worker if request.user == conversation.employer else conversation.employer
    
    # Create message
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        receiver=receiver,
        content=content
    )
    
    # Update conversation timestamp
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])
    
    # Handle file attachments if any
    if request.FILES.getlist('attachments'):
        for file in request.FILES.getlist('attachments'):
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                continue
            MessageAttachment.objects.create(
                message=message,
                file=file,
                filename=file.name,
                file_size=file.size
            )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'content': message.content,
            'sent_at': message.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            'sender': request.user.username
        })
    
    return redirect('chat:conversation_detail', conversation_id=conversation_id)

@login_required
def start_conversation(request, job_id, worker_id=None):
    """Start a new conversation between employer and worker for a job"""
    from django.contrib.auth.models import User
    from jobs.models import JobRequest, JobMatch
    from .models import Conversation
    
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Check if user is either the employer OR a worker who has applied
    is_employer = (request.user == job.employer)
    is_worker_applicant = False
    
    if request.user.profile.user_type == 'worker':
        # Check if worker has applied for this job
        has_match = JobMatch.objects.filter(
            job_request=job, 
            worker=request.user
        ).exists()
        if has_match:
            is_worker_applicant = True
    
    # Allow access if user is employer OR worker applicant
    if not (is_employer or is_worker_applicant):
        messages.error(request, "You don't have permission to start a conversation for this job.")
        if request.user.profile.user_type == 'worker':
            messages.info(request, "You need to apply for this job first before you can message the employer.")
        return redirect('jobs:job_detail', job_id=job.id)
    
    # If worker_id provided, start conversation with specific worker (employer only)
    if worker_id:
        # Only employers can start conversations with specific workers
        if not is_employer:
            messages.error(request, "Only employers can start conversations with specific workers.")
            return redirect('jobs:job_detail', job_id=job.id)
            
        worker = get_object_or_404(User, id=worker_id)
        
        # Prevent employer from messaging themselves
        if worker == request.user:
            messages.error(request, "You cannot start a conversation with yourself.")
            return redirect('jobs:job_detail', job_id=job.id)
        
        # Check if worker has applied for this job
        job_match = JobMatch.objects.filter(
            job_request=job,
            worker=worker
        ).first()
        
        if not job_match:
            messages.error(request, "This worker hasn't applied for this job.")
            return redirect('jobs:job_detail', job_id=job.id)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            job=job,
            employer=request.user,
            worker=worker,
            defaults={'job_match': job_match}
        )
        
        if created:
            messages.success(request, f"Conversation started with {worker.username}")
        else:
            messages.info(request, "Conversation already exists")
        
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    
    # If worker is trying to start conversation with employer
    if request.user.profile.user_type == 'worker':
        # Get the worker's match for this job
        job_match = JobMatch.objects.filter(
            job_request=job,
            worker=request.user
        ).first()
        
        if not job_match:
            messages.error(request, "You need to apply for this job first before messaging the employer.")
            return redirect('jobs:job_detail', job_id=job.id)
        
        # Create conversation from worker side
        conversation, created = Conversation.objects.get_or_create(
            job=job,
            employer=job.employer,
            worker=request.user,
            defaults={'job_match': job_match}
        )
        
        if created:
            messages.success(request, f"Conversation started with {job.employer.username}")
        else:
            messages.info(request, "Conversation already exists")
        
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    
    # Employer view - show page to select worker
    matches = JobMatch.objects.filter(job_request=job).exclude(worker=request.user).select_related('worker')
    
    if not matches.exists():
        messages.warning(request, "No workers have applied for this job yet.")
        return redirect('jobs:job_detail', job_id=job.id)
    
    context = {
        'job': job,
        'matches': matches,
    }
    return render(request, 'chat/select_worker.html', context)

@login_required
def get_unread_count(request):
    """Get unread message count for the current user (for AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    unread_count = Message.objects.filter(
        receiver=request.user,
        is_read=False,
        is_deleted=False
    ).count()
    
    return JsonResponse({'count': unread_count})

@login_required
def mark_conversation_read(request, conversation_id):
    """Mark all messages in a conversation as read"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.user not in [conversation.employer, conversation.worker]:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    conversation.mark_as_read(request.user)
    
    return JsonResponse({'success': True})

@login_required
def delete_conversation(request, conversation_id):
    """Soft delete a conversation for the user"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.user not in [conversation.employer, conversation.worker]:
        raise PermissionDenied("You don't have permission to delete this conversation.")
    
    if request.method == 'POST':
        # Instead of deleting, mark as inactive for this specific user
        # We'll just hide it from their list by marking is_active=False
        # But for now, let's just redirect and show a message
        conversation.is_active = False
        conversation.save()
        messages.success(request, "Conversation archived.")
        return redirect('chat:conversations_list')
    
    context = {
        'conversation': conversation,
    }
    return render(request, 'chat/delete_conversation.html', context)

@login_required
def delete_message(request, message_id):
    """Delete a specific message (soft delete)"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.user not in [message.sender, message.receiver]:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        if request.user == message.sender:
            message.is_deleted_by_sender = True
        else:
            message.is_deleted_by_receiver = True
        
        # If both deleted, mark as fully deleted
        if message.is_deleted_by_sender and message.is_deleted_by_receiver:
            message.is_deleted = True
        
        message.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, "Message deleted.")
        return redirect('chat:conversation_detail', conversation_id=message.conversation.id)
    
    context = {
        'message': message,
    }
    return render(request, 'chat/delete_message.html', context)