from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class CustomUser(AbstractUser):
    """Custom User model for the Gate Pass System"""
    USER_TYPES = [
        ('admin', 'Admin'),
        ('resident', 'Resident'),
        ('security', 'Security'),
        ('guard', 'Security Guard'),  # Legacy support for existing users
    ]
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='resident')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to auto-create Admin profile when user_type is changed to admin"""
        is_new = self.pk is None
        old_user_type = None
        
        if not is_new:
            # Get the old user_type before saving
            try:
                old_instance = CustomUser.objects.get(pk=self.pk)
                old_user_type = old_instance.user_type
            except CustomUser.DoesNotExist:
                old_user_type = None
        
        # Save the CustomUser first
        super().save(*args, **kwargs)
        
        # Check if we're in Django Admin context to avoid conflicts
        # If a profile already exists for this user, don't auto-create
        skip_auto_create = False
        if self.user_type == 'admin' and Admin.objects.filter(user=self).exists():
            skip_auto_create = True
        elif self.user_type == 'resident' and Resident.objects.filter(user=self).exists():
            skip_auto_create = True
        elif self.user_type in ['security', 'guard'] and SecurityGuard.objects.filter(user=self).exists():
            skip_auto_create = True
        
        # DISABLED: Auto-creation functionality moved to Django Admin classes
        # This prevents conflicts between CustomUser.save() and Django Admin creation
        # Profiles are now created only through Django Admin or registration forms
        
        # Auto-delete Admin profile if user_type is changed from 'admin'
        if old_user_type == 'admin' and self.user_type != 'admin':
            try:
                Admin.objects.get(user=self).delete()
            except Admin.DoesNotExist:
                pass

        # Auto-delete Resident profile if user_type is changed from 'resident'
        if old_user_type == 'resident' and self.user_type != 'resident':
            try:
                Resident.objects.get(user=self).delete()
            except Resident.DoesNotExist:
                pass

        # Auto-delete SecurityGuard profile if user_type is changed from 'security' or 'guard'
        if old_user_type in ['security', 'guard'] and self.user_type not in ['security', 'guard']:
            try:
                SecurityGuard.objects.get(user=self).delete()
            except SecurityGuard.DoesNotExist:
                pass


class Resident(models.Model):
    """Model for storing resident information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='resident', null=True, blank=True)
    flat_number = models.CharField(max_length=20)
    building_name = models.CharField(max_length=100, default='Building A')
    phone_number = models.CharField(max_length=10)
    profile_photo = models.ImageField(upload_to='resident_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Resident"
        verbose_name_plural = "Residents"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.flat_number}"


class SecurityGuard(models.Model):
    """Model for storing security guard information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='securityguard', null=True, blank=True)
    employee_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    shift = models.CharField(
        max_length=20,
        choices=[('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night')],
        default='morning'
    )
    profile_photo = models.ImageField(
        upload_to='guard_photos/',
        blank=True,
        null=True,
        help_text="Guard profile photo for identification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Security Guard"
        verbose_name_plural = "Security Guards"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"


class PasswordResetOTP(models.Model):
    """Model for password reset OTPs"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type__in': ['resident', 'security']})
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"
    
    def __str__(self):
        return f"Reset OTP for {self.user.username}"
    
    def is_valid(self):
        """Check if OTP is still valid (uses dashboard settings)"""
        from django.utils import timezone
        try:
            from dashboard.models import DashboardSettings
            expiry_minutes = DashboardSettings.get_settings().otp_expiry_minutes
        except:
            expiry_minutes = 10  # Fallback to 10 minutes
        
        return (not self.is_used and 
                (timezone.now() - self.created_at).total_seconds() < expiry_minutes * 60)


class Admin(models.Model):
    """Model for storing admin information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin', null=True, blank=True)
    admin_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    department = models.CharField(max_length=100, default='Society Management')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Admin"
        verbose_name_plural = "Admins"
    
    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'No User'} - {self.admin_id}"
    
    def save(self, *args, **kwargs):
        # Override save to handle user creation properly
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from django.db import transaction
        
        if not self.pk and not self.user:
            # This is a new admin creation without a user
            with transaction.atomic():
                # Create the user first
                base_username = f"admin_{self.admin_id.lower()}"
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password=f"temp_{username}_123",
                    first_name=f"Admin",
                    last_name=self.admin_id,
                    user_type='admin',
                    phone_number=self.phone_number,
                    is_staff=True,
                    is_superuser=True
                )
                
                # Set the user and save
                self.user = user
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
