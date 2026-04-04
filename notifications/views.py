from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Notification

@login_required
def notification_list(request):
    """View all notifications for the logged-in user"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Mark all as read if requested
    if request.GET.get('mark_all'):
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:list')
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
        'total_count': notifications.count(),
    }
    return render(request, 'notifications/list.html', context)

@login_required
def notification_detail(request, pk):
    """View a single notification"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if notification.link:
        return redirect(notification.link)
    
    return render(request, 'notifications/detail.html', {'notification': notification})

@login_required
def notification_mark_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    messages.success(request, "Notification marked as read.")
    return redirect('notifications:list')

@login_required
def notification_mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')

@login_required
def notification_delete(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    messages.success(request, "Notification deleted.")
    return redirect('notifications:list')

@login_required
def notification_unread_count(request):
    """Get unread notification count (for AJAX)"""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})