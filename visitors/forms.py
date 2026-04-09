from django import forms
from django.contrib.auth.models import User
from accounts.models import Resident
from .models import Visitor, OTP


class VisitorRegistrationForm(forms.ModelForm):
    """Form for registering visitor details - PROJECT REQUIREMENTS COMPLIANT"""
    
    resident = forms.ModelChoiceField(
        queryset=Resident.objects.all().select_related('user').order_by('building_name', 'flat_number'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'resident_select'
        }),
        label='Resident *',
        required=True
    )
    
    class Meta:
        model = Visitor
        fields = ['resident', 'visitor_name', 'mobile_number', 'purpose', 'identity_proof', 'identity_number', 'visitor_photo']
        widgets = {
            'resident': forms.Select(attrs={'class': 'form-control'}),
            'visitor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of Visit'}),
            'identity_proof': forms.Select(attrs={'class': 'form-control'}),
            'identity_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Identity Number'}),
            'visitor_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_mobile_number(self):
        mobile = self.cleaned_data['mobile_number']
        if not mobile.isdigit() or len(mobile) != 10:
            raise forms.ValidationError('Enter a valid 10-digit mobile number.')
        return mobile

    def clean_visitor_name(self):
        name = self.cleaned_data['visitor_name']
        if len(name.strip()) < 3:
            raise forms.ValidationError('Visitor name must be at least 3 characters long.')
        return name.strip()


class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Enter 6-digit OTP',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric'
        }),
        label='One-Time Password (OTP)'
    )


class ResidentApprovalForm(forms.Form):
    """Form for resident to approve/reject visitor"""
    CHOICE = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    action = forms.ChoiceField(choices=CHOICE, widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))


class VisitorHistoryFilterForm(forms.Form):
    """Form for filtering visitor history"""
    from .models import VisitorHistory
    
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + VisitorHistory.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
