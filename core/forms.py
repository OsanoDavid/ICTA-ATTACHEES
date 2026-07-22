from django import forms
from django.db import transaction
from .models import User, AttacheeProfile, Department, WeeklyLog, RegistrationConfig, calculate_default_end_date
from .constants import KENYAN_INSTITUTIONS


class AttacheeRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)
    attachment_end_date = forms.DateField(required=False)
    
    # Convert institution to a dropdown
    institution = forms.ChoiceField(choices=KENYAN_INSTITUTIONS, required=True)

    class Meta:
        model = AttacheeProfile
        fields = [
            'full_name', 'gender', 'national_id', 'registration_number', 'course_name', 
            'institution', 'department', 'attachment_start_date', 'attachment_end_date'
        ]

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, **kwargs)
        if departments:
            self.fields['department'].queryset = departments

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        username = cleaned_data.get('username', '').strip()

        # --- Suffix format enforcement ---
        config = RegistrationConfig.get_config()
        if config is None:
            # No suffix configured by HR — block all registrations
            raise forms.ValidationError(
                "Registrations are currently closed. Please contact HR to open registration."
            )

        required_suffix = config.username_suffix.strip()
        if not username.endswith(required_suffix):
            raise forms.ValidationError(
                "Invalid username format. Please obtain the correct registration instructions from HR."
            )
        # --- End suffix check ---

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")

        start_date = cleaned_data.get('attachment_start_date')
        end_date = cleaned_data.get('attachment_end_date')
        if start_date and not end_date:
            cleaned_data['attachment_end_date'] = calculate_default_end_date(start_date)

        return cleaned_data


    @transaction.atomic
    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data.get('username'),
            email=self.cleaned_data.get('email'),
            password=self.cleaned_data.get('password'),
            role='ATTACHEE'
        )
        profile = super().save(commit=False)
        profile.user = user
        if profile.attachment_start_date and not profile.attachment_end_date:
            profile.attachment_end_date = calculate_default_end_date(profile.attachment_start_date)
        profile.save()
        return profile


# =========================================================
# FIXED: Fields now match your exact WeeklyLog model exactly
# =========================================================
class WeeklyLogForm(forms.ModelForm):
    class Meta:
        model = WeeklyLog
        fields = [
            'week_start_date', 
            'monday_activities', 
            'tuesday_activities', 
            'wednesday_activities', 
            'thursday_activities', 
            'friday_activities'
        ]
        widgets = {
            'week_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monday_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Log Monday tasks...'}),
            'tuesday_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Log Tuesday tasks...'}),
            'wednesday_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Log Wednesday tasks...'}),
            'thursday_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Log Thursday tasks...'}),
            'friday_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Log Friday tasks...'}),
        }