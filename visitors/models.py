from django.db import models
from django.utils import timezone
from accounts.models import Resident, SecurityGuard


class Visitor(models.Model):
    """Model for storing visitor information - PROJECT REQUIREMENTS COMPLIANT"""
    IDENTITY_CHOICES = [
        ('aadhar', 'Aadhar'),
        ('passport', 'Passport'),
        ('license', 'Driving License'),
        ('others', 'Others'),
    ]
    
    visitor_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=10)
    purpose = models.CharField(max_length=200)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='visitors')
    registered_by = models.ForeignKey(SecurityGuard, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_visitors')
    entry_time = models.DateTimeField(null=True, blank=True)  # NULLABLE for existing records
    exit_time = models.DateTimeField(null=True, blank=True)  # Added for exit tracking
    identity_proof = models.CharField(max_length=50, choices=IDENTITY_CHOICES, default='aadhar')
    identity_number = models.CharField(max_length=50, blank=True, null=True)
    visitor_photo = models.ImageField(upload_to='visitor_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.visitor_name} - {self.resident.flat_number}"


class OTP(models.Model):
    """Model for storing OTP verification records"""
    visitor = models.OneToOneField(Visitor, on_delete=models.CASCADE, related_name='otp')
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "OTP"
        verbose_name_plural = "OTPs"
        ordering = ['-created_at']
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (not self.is_verified and 
                timezone.now() < self.expires_at and 
                self.attempts < 3)
    
    def verify_otp(self, entered_otp):
        """Verify OTP"""
        if not self.is_valid():
            return False
        
        if self.attempts >= 3:
            # Log security event for brute force attempt
            from core.utils import log_activity
            log_activity(None, 'security_breach', f'OTP brute force attempt for visitor {self.visitor.visitor_name}', None, target_id=self.visitor.id)
            return False
        
        if self.otp_code == entered_otp:
            self.is_verified = True
            self.save()
            return True
        else:
            self.attempts += 1
            self.save()
            return False
    
    def __str__(self):
        return f"OTP for {self.visitor.visitor_name}"


class GatePass(models.Model):
    """Model for storing gate pass approval records"""
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('pending', 'Pending'),
    ]
    
    visitor = models.OneToOneField(Visitor, on_delete=models.CASCADE, related_name='gatepass')
    pass_id = models.CharField(max_length=20, unique=True)
    issue_time = models.DateTimeField(auto_now_add=True)
    valid_till = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Gate Pass"
        verbose_name_plural = "Gate Passes"
        ordering = ['-issue_time']
    
    def save(self, *args, **kwargs):
        if not self.pass_id:
            self.pass_id = self.generate_pass_id()
        super().save(*args, **kwargs)
    
    def generate_pass_id(self):
        """Generate unique gate pass ID"""
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"GP{timestamp}{random_str}"
    
    def is_valid(self):
        """Check if gate pass is still valid"""
        return (self.status == 'approved' and 
                timezone.now() < self.valid_till)
    
    def __str__(self):
        return f"Gate Pass {self.pass_id} - {self.visitor.visitor_name}"


class VisitorHistory(models.Model):
    """Model for storing visitor entry/exit tracking events"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_process', 'In Process'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visitorhistory')
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(blank=True, null=True)
    purpose = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Visitor History"
        verbose_name_plural = "Visitor Histories"
        ordering = ['-created_at']
    
    def duration(self):
        """Calculate visit duration"""
        if self.exit_time and self.entry_time:
            return self.exit_time - self.entry_time
        return None
    
    def get_duration_display(self):
        """Get formatted duration display"""
        duration = self.duration()
        if duration:
            total_seconds = duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m"
            else:
                return "Less than 1m"
        return "N/A"
    
    def __str__(self):
        return f"{self.visitor.visitor_name} - {self.status}"
