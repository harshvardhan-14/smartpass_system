from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class SystemAudit(models.Model):
    """Comprehensive system audit log model"""
    
    ACTION_TYPES = [
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('user_create', 'User Creation'),
        ('user_update', 'User Update'),
        ('user_delete', 'User Deletion'),
        ('visitor_register', 'Visitor Registration'),
        ('visitor_approve', 'Visitor Approval'),
        ('visitor_reject', 'Visitor Rejection'),
        ('visitor_exit', 'Visitor Exit'),
        ('otp_generate', 'OTP Generation'),
        ('otp_verify', 'OTP Verification'),
        ('gate_pass_issue', 'Gate Pass Issued'),
        ('gate_pass_revoke', 'Gate Pass Revoked'),
        ('system_error', 'System Error'),
        ('security_breach', 'Security Breach'),
        ('data_export', 'Data Export'),
        ('config_change', 'Configuration Change'),
    ]
    
    STATUS_TYPES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
        ('warning', 'Warning'),
        ('info', 'Information'),
    ]
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_TYPES, default='success')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    class Meta:
        verbose_name = "System Audit"
        verbose_name_plural = "System Audits"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action_type', 'timestamp']),
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['action_type']),
        ]
    
    def __str__(self):
        user_name = self.user.username if self.user else 'Anonymous'
        return f"{user_name} - {self.get_action_type_display()} - {self.timestamp}"
    
    @property
    def formatted_timestamp(self):
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def formatted_old_values(self):
        if self.old_values:
            return json.dumps(self.old_values, indent=2, ensure_ascii=False)
        return '{}'
    
    @property
    def formatted_new_values(self):
        if self.new_values:
            return json.dumps(self.new_values, indent=2, ensure_ascii=False)
        return '{}'
