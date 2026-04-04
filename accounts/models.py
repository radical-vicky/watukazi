from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    USER_TYPES = (
        ('worker', 'Worker - Looking for jobs'),
        ('employer', 'Employer - Looking to hire workers'),
        ('admin', 'Administrator'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='worker')
    phone_number = models.CharField(max_length=15, unique=True)
    location = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=50, blank=True)
    sub_county = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"
    
    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}" or self.user.username

class SMSSettings(models.Model):
    """SMS configuration settings"""
    phone_number = models.CharField(max_length=15, default='0700000000', help_text="SMS number for users to text")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "SMS Settings"
    
    def __str__(self):
        return f"SMS Number: {self.phone_number}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            phone_number=f"TEMP_{instance.id}",
            user_type='worker'
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()