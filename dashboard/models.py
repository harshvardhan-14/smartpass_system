from django.db import models
from django.conf import settings


class DashboardSettings(models.Model):
    """Dashboard system settings"""
    
    # OTP Settings
    otp_expiry_minutes = models.PositiveIntegerField(default=5, help_text="OTP expiry time in minutes")
    max_otp_attempts = models.PositiveIntegerField(default=3, help_text="Maximum OTP attempts allowed")
    
    # System Settings
    enable_notifications = models.BooleanField(default=True, help_text="Enable system notifications")
    auto_cleanup_days = models.PositiveIntegerField(default=30, help_text="Auto cleanup old records after days")
    
    # Display Settings
    items_per_page = models.PositiveIntegerField(default=10, help_text="Number of items per page in lists")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dashboard Settings"
        verbose_name_plural = "Dashboard Settings"
    
    def __str__(self):
        return f"Settings (Updated: {self.updated_at.strftime('%Y-%m-%d')})"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)
