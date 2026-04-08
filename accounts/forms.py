from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile

class WorkerSignupForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '0712345678'})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Nairobi'})
    )
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number',
                 'location', 'password1', 'password2')
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and Profile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Check if profile already exists (created by signal)
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': self.cleaned_data['phone_number'],
                    'user_type': 'worker',
                    'location': self.cleaned_data.get('location', '')
                }
            )
            
            if not created:
                # Update existing profile
                profile.phone_number = self.cleaned_data['phone_number']
                profile.user_type = 'worker'
                profile.location = self.cleaned_data.get('location', '')
                profile.save()
            
            # Create worker profile
            from workers.models import WorkerProfile
            WorkerProfile.objects.get_or_create(user=user)
        
        return user

class EmployerSignupForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '0712345678'})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Nairobi'})
    )
    company_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Your Company Name'})
    )
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number',
                 'location', 'company_name', 'password1', 'password2')
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and Profile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Check if profile already exists (created by signal)
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': self.cleaned_data['phone_number'],
                    'user_type': 'employer',
                    'location': self.cleaned_data.get('location', '')
                }
            )
            
            if not created:
                # Update existing profile
                profile.phone_number = self.cleaned_data['phone_number']
                profile.user_type = 'employer'  # Force to employer
                profile.location = self.cleaned_data.get('location', '')
                profile.save()
            
            # Create employer profile
            from employers.models import EmployerProfile
            employer_profile, created = EmployerProfile.objects.get_or_create(user=user)
            employer_profile.company_name = self.cleaned_data.get('company_name', '')
            employer_profile.save()
        
        return user

class WorkerLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, 'profile') or user.profile.user_type != 'worker':
            raise forms.ValidationError(
                "This account is not a worker account. Please use the employer login page.",
                code='invalid_login',
            )

class EmployerLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, 'profile') or user.profile.user_type != 'employer':
            raise forms.ValidationError(
                "This account is not an employer account. Please use the worker login page.",
                code='invalid_login',
            )