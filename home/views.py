from django.shortcuts import render
from .models import HeroBanner, FeatureImage
from accounts.models import SMSSettings

def home_page(request):
    """Home page view with dynamic images from database"""
    # Get active hero banners
    hero_banners = HeroBanner.objects.filter(is_active=True)
    
    # Get active feature images
    feature_images = FeatureImage.objects.filter(is_active=True)
    
    # Get SMS number from settings
    sms_settings = SMSSettings.objects.first()
    sms_number = sms_settings.phone_number if sms_settings else '0700000000'
    
    context = {
        'hero_banners': hero_banners,
        'feature_images': feature_images,
        'sms_number': sms_number,
    }
    return render(request, 'home.html', context)