"""
Services for visitor management system
"""
import random
import string
from django.conf import settings
from django.utils import timezone
from decouple import config


class OTPService:
    """Service for generating and sending OTPs"""
    
    @staticmethod
    def generate_otp(length=6):
        """Generate random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_otp(phone_number, otp_code, resident_name):
        """Send OTP via SMS"""
        from django.conf import settings
        
        # Try to send via Twilio if configured
        if (hasattr(settings, 'TWILIO_ACCOUNT_SID') and 
            settings.TWILIO_ACCOUNT_SID and 
            settings.TWILIO_AUTH_TOKEN and 
            settings.TWILIO_PHONE_NUMBER):
            
            try:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                
                message = client.messages.create(
                    body=f"Your OTP for Smart Gate Pass System is: {otp_code}. Valid for 5 minutes.",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=f"+91{phone_number}"
                )
                
                print(f"✅ SMS sent successfully via Twilio")
                print(f"   Message SID: {message.sid}")
                print(f"   To: +91{phone_number}")
                print(f"   OTP: {otp_code}")
                return True
                
            except Exception as e:
                print(f"❌ Twilio SMS failed: {e}")
                print(f"🔔 Falling back to console output:")
                print(f"   To: {phone_number}")
                print(f"   Resident: {resident_name}")
                print(f"   OTP: {otp_code}")
                print(f"   Time: {timezone.now()}")
                return True
        else:
            # Development mode - print to console
            print(f"🔔 OTP Service (Development Mode):")
            print(f"   To: {phone_number}")
            print(f"   Resident: {resident_name}")
            print(f"   OTP: {otp_code}")
            print(f"   Time: {timezone.now()}")
            print(f"💡 To enable SMS, configure Twilio settings in .env file")
            return True
    
    @staticmethod
    def verify_otp(otp_obj, entered_otp):
        """Verify OTP"""
        if not otp_obj.is_valid():
            return False
        
        if otp_obj.otp_code == entered_otp:
            otp_obj.is_verified = True
            otp_obj.save()
            return True
        else:
            otp_obj.attempts += 1
            otp_obj.save()
            return False


class GatePassService:
    """Service for managing gate passes"""
    
    @staticmethod
    def generate_gate_pass_id():
        """Generate unique gate pass ID"""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"GP{timestamp}{random_str}"
    
    @staticmethod
    def create_gate_pass(visitor, valid_hours=24):
        """Create a new gate pass"""
        from .models import GatePass
        
        return GatePass.objects.create(
            visitor=visitor,
            pass_id=GatePassService.generate_gate_pass_id(),
            valid_till=timezone.now() + timezone.timedelta(hours=valid_hours)
        )
    
    @staticmethod
    def is_gate_pass_valid(gate_pass):
        """Check if gate pass is still valid"""
        return (gate_pass.status == 'approved' and 
                timezone.now() < gate_pass.valid_till)


class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    def create_visitor_notification(resident, visitor, notification_type):
        """Create notification for visitor-related events"""
        from notifications.models import Notification
        
        if notification_type == 'visitor_request':
            title = 'New Visitor Request'
            message = f'Visitor {visitor.visitor_name} is waiting for your approval.'
        elif notification_type == 'visitor_approved':
            title = 'Visitor Approved'
            message = f'Visitor {visitor.visitor_name} has been approved.'
        elif notification_type == 'visitor_rejected':
            title = 'Visitor Rejected'
            message = f'Visitor {visitor.visitor_name} has been rejected.'
        else:
            return None
        
        return Notification.objects.create(
            user=resident.user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_model='Visitor',
            related_id=visitor.id
        )
    
    @staticmethod
    def create_gate_pass_notification(resident, gate_pass):
        """Create notification for gate pass issuance"""
        from notifications.models import Notification
        
        return Notification.objects.create(
            user=resident.user,
            notification_type='gate_pass_issued',
            title='Gate Pass Issued',
            message=f'Gate pass {gate_pass.pass_id} has been issued for visitor {gate_pass.visitor.visitor_name}.',
            related_model='GatePass',
            related_id=gate_pass.id
        )


class VisitorService:
    """Service for visitor management operations"""
    
    @staticmethod
    def get_visitor_statistics():
        """Get visitor statistics"""
        from .models import Visitor, VisitorHistory
        
        today = timezone.now().date()
        
        return {
            'total_visitors': Visitor.objects.count(),
            'today_visitors': Visitor.objects.filter(entry_time__date=today).count(),
            'active_visitors': Visitor.objects.filter(exit_time__isnull=True).count(),
            'approved_visitors': VisitorHistory.objects.filter(status='approved').count(),
            'rejected_visitors': VisitorHistory.objects.filter(status='rejected').count(),
            'pending_visitors': VisitorHistory.objects.filter(status='pending').count(),
        }
    
    @staticmethod
    def get_resident_visitor_history(resident, days=30):
        """Get visitor history for a resident"""
        from .models import VisitorHistory
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        return VisitorHistory.objects.filter(
            resident=resident,
            created_at__gte=start_date
        ).order_by('-created_at')
    
    @staticmethod
    def get_guard_visitor_statistics(guard):
        """Get visitor statistics for a security guard"""
        from .models import Visitor
        
        today = timezone.now().date()
        
        return {
            'total_registered': Visitor.objects.filter(registered_by=guard).count(),
            'today_registered': Visitor.objects.filter(
                registered_by=guard,
                entry_time__date=today
            ).count(),
            'active_visitors': Visitor.objects.filter(
                registered_by=guard,
                exit_time__isnull=True
            ).count(),
        }
