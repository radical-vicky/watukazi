from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import Profile, SMSSettings
from workers.models import WorkerProfile
from employers.models import EmployerProfile

class ProfileInline(admin.StackedInline):
    """Inline profile editing in user admin"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('user_type', 'phone_number', 'location', 'county', 'sub_county', 'is_verified')

class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with profile fields"""
    phone_number = forms.CharField(max_length=15, required=True, help_text="Required")
    user_type = forms.ChoiceField(choices=Profile.USER_TYPES, required=True, initial='worker')
    location = forms.CharField(max_length=100, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data.get('phone_number')
            profile.user_type = self.cleaned_data.get('user_type', 'worker')
            profile.location = self.cleaned_data.get('location', '')
            profile.save()
            
            # Create specific profile based on user type
            if profile.user_type == 'worker':
                WorkerProfile.objects.get_or_create(user=user)
            elif profile.user_type == 'employer':
                EmployerProfile.objects.get_or_create(user=user)
        return user

class CustomUserChangeForm(UserChangeForm):
    """Custom user change form with profile fields"""
    phone_number = forms.CharField(max_length=15, required=True)
    user_type = forms.ChoiceField(choices=Profile.USER_TYPES, required=True)
    location = forms.CharField(max_length=100, required=False)
    county = forms.CharField(max_length=50, required=False)
    sub_county = forms.CharField(max_length=50, required=False)
    is_verified = forms.BooleanField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone_number'].initial = self.instance.profile.phone_number
            self.fields['user_type'].initial = self.instance.profile.user_type
            self.fields['location'].initial = self.instance.profile.location
            self.fields['county'].initial = self.instance.profile.county
            self.fields['sub_county'].initial = self.instance.profile.sub_county
            self.fields['is_verified'].initial = self.instance.profile.is_verified
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            if hasattr(user, 'profile'):
                user.profile.phone_number = self.cleaned_data.get('phone_number')
                user.profile.user_type = self.cleaned_data.get('user_type')
                user.profile.location = self.cleaned_data.get('location', '')
                user.profile.county = self.cleaned_data.get('county', '')
                user.profile.sub_county = self.cleaned_data.get('sub_county', '')
                user.profile.is_verified = self.cleaned_data.get('is_verified', False)
                user.profile.save()

class CustomUserAdmin(UserAdmin):
    """Custom User Admin with profile integration"""
    inlines = [ProfileInline]
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_phone', 'get_user_type', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'profile__user_type', 'profile__is_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__phone_number')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    def get_phone(self, obj):
        return obj.profile.phone_number if hasattr(obj, 'profile') else '-'
    get_phone.short_description = 'Phone Number'
    
    def get_user_type(self, obj):
        return obj.profile.get_user_type_display() if hasattr(obj, 'profile') else '-'
    get_user_type.short_description = 'User Type'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# SMS Settings Admin
@admin.register(SMSSettings)
class SMSSettingsAdmin(admin.ModelAdmin):
    """Admin for SMS settings"""
    list_display = ('phone_number', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    fieldsets = (
        ('SMS Configuration', {
            'fields': ('phone_number', 'is_active'),
            'description': 'Configure the SMS number that users will text for job applications and commands.'
        }),
        ('Information', {
            'fields': ('updated_at',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Only allow one instance
        if SMSSettings.objects.exists():
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False

# Register Profile separately
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone_number', 'location', 'is_verified', 'created_at')
    list_filter = ('user_type', 'is_verified', 'created_at')
    search_fields = ('user__username', 'phone_number', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_type', 'phone_number')
        }),
        ('Location Information', {
            'fields': ('location', 'county', 'sub_county')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)