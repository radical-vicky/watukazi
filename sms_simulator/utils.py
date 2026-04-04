from django.utils import timezone
from .models import SMSLog

def send_sms(phone_number, message):
    """
    Simulate sending an SMS
    In production, replace with Africa's Talking API integration
    """
    print(f"\n{'='*60}")
    print(f"📱 SMS SIMULATOR - OUTGOING")
    print(f"{'='*60}")
    print(f"TO: {phone_number}")
    print(f"MESSAGE: {message}")
    print(f"TIME: {timezone.now()}")
    print(f"{'='*60}\n")
    
    # Log to database
    try:
        sms_log = SMSLog.objects.create(
            phone_number=phone_number,
            message=message,
            direction='outgoing',
            status='delivered',
            delivered_at=timezone.now()
        )
        return True, sms_log.id
    except Exception as e:
        print(f"Error logging SMS: {e}")
        return False, None

def receive_sms(phone_number, message):
    """
    Simulate receiving an SMS
    """
    print(f"\n{'='*60}")
    print(f"📱 SMS SIMULATOR - INCOMING")
    print(f"{'='*60}")
    print(f"FROM: {phone_number}")
    print(f"MESSAGE: {message}")
    print(f"TIME: {timezone.now()}")
    print(f"{'='*60}\n")
    
    # Log to database
    try:
        sms_log = SMSLog.objects.create(
            phone_number=phone_number,
            message=message,
            direction='incoming',
            status='delivered',
            delivered_at=timezone.now()
        )
        return True, sms_log.id
    except Exception as e:
        print(f"Error logging SMS: {e}")
        return False, None

def send_bulk_sms(phone_numbers, message):
    """
    Send bulk SMS to multiple recipients
    """
    results = []
    for phone_number in phone_numbers:
        success, log_id = send_sms(phone_number, message)
        results.append({
            'phone_number': phone_number,
            'success': success,
            'log_id': log_id
        })
    return results