from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import CustomUser, Resident, SecurityGuard, Admin

class ResidentCreationForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Resident
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'flat_number', 'phone_number', 'building_name']
        widgets = {
            'flat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'building_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SecurityGuardCreationForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = SecurityGuard
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'employee_id', 'phone_number', 'shift']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'shift': forms.Select(attrs={'class': 'form-control'}),
        }

class AdminCreationForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Admin
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'admin_id', 'phone_number', 'department']
        widgets = {
            'admin_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CustomUserAdmin(UserAdmin):
    """Custom admin for CustomUser model"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    """Admin configuration for Resident model"""
    list_display = ('user', 'flat_number', 'phone_number', 'building_name', 'created_at')
    list_filter = ('building_name', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'flat_number', 'phone_number')
    ordering = ('-created_at',)
    
    form = ResidentCreationForm
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            from django.contrib.auth import get_user_model
            User = get_user_model()
            from django.db import transaction
            
            with transaction.atomic():
                # Create the CustomUser with form data
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                password = form.cleaned_data['password']
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='resident',
                    phone_number=obj.phone_number
                )
                
                # Now create the Resident object with the user
                obj.user = user
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


@admin.register(SecurityGuard)
class SecurityGuardAdmin(admin.ModelAdmin):
    """Admin configuration for SecurityGuard model"""
    list_display = ('user', 'employee_id', 'phone_number', 'shift', 'created_at')
    list_filter = ('shift', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id', 'phone_number')
    ordering = ('-created_at',)
    
    form = SecurityGuardCreationForm
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            from django.contrib.auth import get_user_model
            User = get_user_model()
            from django.db import transaction
            
            with transaction.atomic():
                # Create the CustomUser with form data
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                password = form.cleaned_data['password']
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='security',
                    phone_number=obj.phone_number
                )
                
                # Now create the SecurityGuard object with the user
                obj.user = user
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    """Admin configuration for Admin model"""
    list_display = ('user', 'admin_id', 'phone_number', 'department', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'admin_id', 'phone_number')
    ordering = ('-created_at',)
    
    form = AdminCreationForm
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            from django.contrib.auth import get_user_model
            User = get_user_model()
            from django.db import transaction
            
            with transaction.atomic():
                # Create the CustomUser with form data
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                password = form.cleaned_data['password']
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='admin',
                    phone_number=obj.phone_number,
                    is_staff=True,
                    is_superuser=True
                )
                
                # Now create the Admin object with the user
                obj.user = user
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)
