from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import SMSLog
from .utils import send_sms, receive_sms
from .sms_processor import process_sms_command

@staff_member_required
def sms_dashboard(request):
    """SMS Dashboard"""
    total_sms = SMSLog.objects.count()
    sent_sms = SMSLog.objects.filter(direction='outgoing').count()
    received_sms = SMSLog.objects.filter(direction='incoming').count()
    recent_sms = SMSLog.objects.all().order_by('-created_at')[:20]
    
    context = {
        'total_sms': total_sms,
        'sent_sms': sent_sms,
        'received_sms': received_sms,
        'recent_sms': recent_sms,
    }
    return render(request, 'sms_simulator/dashboard.html', context)

@staff_member_required
def sms_logs(request):
    """View all SMS logs"""
    logs = SMSLog.objects.all().order_by('-created_at')
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
    }
    return render(request, 'sms_simulator/logs.html', context)

@login_required
def send_sms_form(request):
    """Send SMS form"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        message = request.POST.get('message')
        
        if phone_number and message:
            send_sms(phone_number, message)
            messages.success(request, f"SMS sent to {phone_number}")
        else:
            messages.error(request, "Please provide both phone number and message")
        
        return redirect('sms_simulator:logs')
    
    return render(request, 'sms_simulator/send.html')

@csrf_exempt
@require_http_methods(["POST"])
def sms_webhook(request):
    """
    Webhook endpoint for receiving SMS from Africa's Talking
    CSRF exempt because this is an external API endpoint
    """
    try:
        # Get phone number and message from request
        # Support multiple formats (Africa's Talking, Twilio, custom)
        phone_number = request.POST.get('from') or request.POST.get('phone_number') or request.POST.get('msisdn')
        message = request.POST.get('text') or request.POST.get('message')
        
        # Also check JSON body
        if not phone_number and request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            phone_number = data.get('from') or data.get('phone_number')
            message = data.get('text') or data.get('message')
        
        if not phone_number or not message:
            return JsonResponse({
                'status': 'error', 
                'message': 'Missing phone_number or message. Please provide both fields.'
            }, status=400)
        
        # Clean phone number (remove any non-digit characters except +)
        phone_number = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Log received SMS
        receive_sms(phone_number, message)
        
        # Process the SMS command
        process_sms_command(phone_number, message)
        
        return JsonResponse({
            'status': 'success', 
            'message': 'SMS processed successfully',
            'phone_number': phone_number
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)