from django import forms
from django.contrib.auth.models import User
from .models import Resident, SecurityGuard, CustomUser
import uuid
from datetime import datetime


def generate_employee_id():
    """Generate unique employee ID"""
    # Generate ID like EMP2026001234 (year + random)
    year = datetime.now().year
    random_num = str(uuid.uuid4().int)[:6]
    employee_id = f"EMP{year}{random_num}"
    
    # Ensure uniqueness
    while SecurityGuard.objects.filter(employee_id=employee_id).exists():
        random_num = str(uuid.uuid4().int)[:6]
        employee_id = f"EMP{year}{random_num}"
    
    return employee_id


class ForgotPasswordForm(forms.Form):
    """Form for forgot password - mobile number only"""
    mobile_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your 10-digit mobile number'
        })
    )
    
    def clean_mobile_number(self):
        """Validate the mobile number"""
        mobile_number = self.cleaned_data['mobile_number']
        
        # Remove any non-digit characters
        mobile_number = ''.join(filter(str.isdigit, mobile_number))
        
        # Check if it's exactly 10 digits
        if len(mobile_number) != 10:
            raise forms.ValidationError("Mobile number must be exactly 10 digits")
        
        return mobile_number


class ResetPasswordForm(forms.Form):
    """Form for password reset with OTP"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric'
        }),
        label='One-Time Password (OTP)'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        label='New Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data


class ResidentRegistrationForm(forms.Form):
    """Form for registering resident"""
    # User fields
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}))
    
    # Profile fields
    flat_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A-101'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}))
    building_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Building Name'}))
    profile_photo = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        required=False,
        help_text="Optional: Upload your profile photo"
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data


class SecurityGuardRegistrationForm(forms.Form):
    """Form for registering security guard with photo upload"""
    # User fields
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}))
    
    # Profile fields
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}))
    shift = forms.ChoiceField(
        choices=[('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='morning'
    )
    
    profile_photo = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'capture': 'camera',
            'id': 'profile_photo'
        }),
        label='Profile Photo',
        required=False,
        help_text='Upload a clear photo of your face (JPEG/PNG, max 5MB)'
    )
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email
    
    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Photo size should be less than 5MB')
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if photo.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG and PNG images are allowed')
        return photo
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data
