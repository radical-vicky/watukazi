from .models import SMSSettings

def sms_settings(request):
    """Add SMS settings to all templates"""
    try:
        sms = SMSSettings.objects.first()
        sms_number = sms.phone_number if sms else '0700000000'
    except:
        sms_number = '0700000000'
    
    return {
        'sms_number': sms_number,
    }