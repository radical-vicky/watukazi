from django import forms
from .models import WorkerProfile, Skill

class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = ['bio', 'years_experience', 'hourly_rate', 'daily_rate', 'availability_status', 
                  'id_number', 'profile_image', 'id_image']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell employers about your skills, experience, and what makes you unique...'}),
            'years_experience': forms.NumberInput(attrs={'min': 0, 'placeholder': 'e.g., 5'}),
            'hourly_rate': forms.NumberInput(attrs={'placeholder': 'e.g., 500'}),
            'daily_rate': forms.NumberInput(attrs={'placeholder': 'e.g., 3500'}),
            'id_number': forms.TextInput(attrs={'placeholder': 'e.g., 12345678'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bio'].help_text = "Describe your skills, experience, and services you offer"
        self.fields['years_experience'].help_text = "Number of years of experience"
        self.fields['hourly_rate'].help_text = "Your hourly rate in KES (optional)"
        self.fields['daily_rate'].help_text = "Your daily rate in KES (optional)"
        self.fields['id_number'].help_text = "National ID or Passport Number for verification"
        self.fields['profile_image'].help_text = "Upload a profile picture (optional)"
        self.fields['id_image'].help_text = "Upload your National ID or Passport for verification"
        
        # Make id_number required for verification
        self.fields['id_number'].required = False
        
        # Add current image display if exists
        if self.instance and self.instance.profile_image:
            self.fields['profile_image'].help_text = f"Current: {self.instance.profile_image.name}"
        if self.instance and self.instance.id_image:
            self.fields['id_image'].help_text = f"Current ID uploaded"

class SkillSelectionForm(forms.Form):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select your skills"
    )