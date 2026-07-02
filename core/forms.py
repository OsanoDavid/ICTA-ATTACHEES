from django import forms
from django.db import transaction
from .models import User, AttacheeProfile, Department, WeeklyLog
from .constants import KENYAN_INSTITUTIONS

class AttacheeRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)
    
    # Convert institution to a dropdown
    institution = forms.ChoiceField(choices=KENYAN_INSTITUTIONS, required=True)

    class Meta:
        model = AttacheeProfile
        fields = [
            'full_name', 'gender', 'registration_number', 'course_name', 
            'institution', 'department', 'attachment_start_date'
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

        if User.objects.filter(username=cleaned_data.get('username')).exists():
            raise forms.ValidationError("A user with this username already exists.")

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