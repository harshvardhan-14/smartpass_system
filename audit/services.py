"""
Audit Service for tracking all system activities
"""
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.serializers.json import DjangoJSONEncoder
import json

from accounts.models import CustomUser
from .models import SystemAudit


class AuditService:
    """Service for logging system activities"""
    
    @staticmethod
    def log_activity(user, action_type, description, target_model='', target_id=None, 
                     old_values=None, new_values=None, status='success', request=None):
        """
        Log system activity
        """
        ip_address = None
        user_agent = ''
        
        if request:
            from core.utils import get_client_ip
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        audit = SystemAudit.objects.create(
            user=user,
            action_type=action_type,
            description=description,
            target_model=target_model,
            target_id=target_id,
            old_values=old_values,
            new_values=new_values,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return audit
    
    @staticmethod
    def log_login(user, request):
        """Log user login"""
        return AuditService.log_activity(
            user=user,
            action_type='user_login',
            description=f'User {user.username} logged in successfully',
            request=request
        )
    
    @staticmethod
    def log_logout(user, request):
        """Log user logout"""
        return AuditService.log_activity(
            user=user,
            action_type='user_logout',
            description=f'User {user.username} logged out',
            request=request
        )
    
    @staticmethod
    def log_user_created(user, created_by):
        """Log user creation"""
        return AuditService.log_activity(
            user=created_by,
            action_type='user_create',
            description=f'User {user.username} ({user.get_user_type_display()}) created',
            target_model='CustomUser',
            target_id=user.id,
            new_values={
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        )
    
    @staticmethod
    def log_visitor_registration(visitor, security_guard, request):
        """Log visitor registration"""
        return AuditService.log_activity(
            user=security_guard.user,
            action_type='visitor_register',
            description=f'Visitor {visitor.visitor_name} registered for {visitor.resident.flat_number}',
            target_model='Visitor',
            target_id=visitor.id,
            new_values={
                'visitor_name': visitor.visitor_name,
                'mobile_number': visitor.mobile_number,
                'purpose': visitor.purpose,
                'resident': visitor.resident.flat_number
            },
            request=request
        )
    
    @staticmethod
    def log_otp_generated(visitor, security_guard, request):
        """Log OTP generation"""
        return AuditService.log_activity(
            user=security_guard.user,
            action_type='otp_generate',
            description=f'OTP generated for visitor {visitor.visitor_name}',
            target_model='OTP',
            target_id=visitor.otp.id if hasattr(visitor, 'otp') and visitor.otp else None,
            request=request
        )
    
    @staticmethod
    def log_otp_verified(visitor, security_guard, request):
        """Log OTP verification"""
        return AuditService.log_activity(
            user=security_guard.user,
            action_type='otp_verify',
            description=f'OTP verified for visitor {visitor.visitor_name}',
            target_model='OTP',
            target_id=visitor.otp.id if hasattr(visitor, 'otp') and visitor.otp else None,
            request=request
        )
    
    @staticmethod
    def log_gate_pass_issued(gate_pass, security_guard, request):
        """Log gate pass issuance"""
        return AuditService.log_activity(
            user=security_guard.user,
            action_type='gate_pass_issue',
            description=f'Gate pass {gate_pass.pass_id} issued for visitor {gate_pass.visitor.visitor_name}',
            target_model='GatePass',
            target_id=gate_pass.id,
            new_values={
                'pass_id': gate_pass.pass_id,
                'visitor': gate_pass.visitor.visitor_name,
                'resident': gate_pass.visitor.resident.flat_number,
                'valid_till': gate_pass.valid_till.isoformat()
            },
            request=request
        )
    
    @staticmethod
    def log_visitor_approval(visitor, resident, request):
        """Log visitor approval"""
        return AuditService.log_activity(
            user=resident.user,
            action_type='visitor_approve',
            description=f'Visitor {visitor.visitor_name} approved by resident {resident.flat_number}',
            target_model='Visitor',
            target_id=visitor.id,
            request=request
        )
    
    @staticmethod
    def log_visitor_rejection(visitor, resident, request):
        """Log visitor rejection"""
        return AuditService.log_activity(
            user=resident.user,
            action_type='visitor_reject',
            description=f'Visitor {visitor.visitor_name} rejected by resident {resident.flat_number}',
            target_model='Visitor',
            target_id=visitor.id,
            request=request
        )
    
    @staticmethod
    def log_visitor_exit(visitor, security_guard, request):
        """Log visitor exit"""
        return AuditService.log_activity(
            user=security_guard.user,
            action_type='visitor_exit',
            description=f'Visitor {visitor.visitor_name} marked as exited',
            target_model='Visitor',
            target_id=visitor.id,
            new_values={'exit_time': visitor.exit_time.isoformat() if visitor.exit_time else None},
            request=request
        )
    
    @staticmethod
    def log_system_error(error_message, request=None, user=None):
        """Log system error"""
        return AuditService.log_activity(
            user=user,
            action_type='system_error',
            description=f'System error: {error_message}',
            status='failure',
            request=request
        )
    
    @staticmethod
    def log_security_breach(description, request=None, user=None):
        """Log security breach"""
        return AuditService.log_activity(
            user=user,
            action_type='security_breach',
            description=f'Security breach: {description}',
            status='warning',
            request=request
        )
    
    @staticmethod
    def get_audit_statistics():
        """Get audit statistics"""
        return {
            'total_activities': SystemAudit.objects.count(),
            'today_activities': SystemAudit.objects.filter(
                timestamp__date=timezone.now().date()
            ).count(),
            'failed_activities': SystemAudit.objects.filter(status='failure').count(),
            'security_events': SystemAudit.objects.filter(
                action_type__in=['system_error', 'security_breach']
            ).count(),
            'user_logins': SystemAudit.objects.filter(action_type='user_login').count(),
            'visitor_activities': SystemAudit.objects.filter(
                action_type__startswith='visitor'
            ).count(),
        }
    
    @staticmethod
    def get_recent_activities(limit=50):
        """Get recent audit activities"""
        return SystemAudit.objects.select_related('user').order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_user_activities(user, limit=20):
        """Get activities for a specific user"""
        return SystemAudit.objects.filter(user=user).order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_activities_by_type(action_type, limit=50):
        """Get activities by type"""
        return SystemAudit.objects.filter(action_type=action_type).order_by('-timestamp')[:limit]


# Django signal handlers
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Signal handler for user login"""
    AuditService.log_login(user, request)


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Signal handler for user logout"""
    AuditService.log_logout(user, request)


@receiver(post_save, sender=CustomUser)
def log_user_creation(sender, instance, created, **kwargs):
    """Signal handler for user creation"""
    if created:
        AuditService.log_activity(
            user=None,
            action_type='user_create',
            description=f'User {instance.username} ({instance.get_user_type_display()}) created',
            target_model='CustomUser',
            target_id=instance.id,
        )
