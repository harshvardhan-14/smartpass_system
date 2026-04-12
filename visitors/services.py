"""
Services for visitor management system.
"""
import logging
import random
import string
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class OTPService:
    """Service for generating and sending OTPs."""

    @staticmethod
    def generate_otp(length=6):
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def send_otp(phone_number, otp_code, resident_name):
        """Send OTP via Twilio SMS, falling back to log output in dev mode."""
        if (
            getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            and getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            and getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        ):
            try:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=f'Your OTP for Smart Gate Pass System is: {otp_code}. Valid for 5 minutes.',
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=f'+91{phone_number}',
                )
                logger.info('OTP SMS sent via Twilio. SID=%s To=+91%s', message.sid, phone_number)
                return True
            except Exception as exc:
                logger.error('Twilio SMS failed: %s – logging OTP to console for dev.', exc)

        # Development / fallback: emit OTP to log (NOT production-safe)
        logger.warning(
            'OTP (dev-mode): phone=%s resident=%s otp=%s time=%s',
            phone_number, resident_name, otp_code, timezone.now(),
        )
        return True

    @staticmethod
    def verify_otp(otp_obj, entered_otp):
        if not otp_obj.is_valid():
            return False
        if otp_obj.otp_code == entered_otp:
            otp_obj.is_verified = True
            otp_obj.save()
            return True
        otp_obj.attempts += 1
        otp_obj.save()
        return False


class GatePassService:
    """Service for managing gate passes."""

    @staticmethod
    def generate_gate_pass_id():
        timestamp = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f'GP{timestamp}{random_str}'

    @staticmethod
    def create_gate_pass(visitor, valid_hours=24):
        from .models import GatePass
        return GatePass.objects.create(
            visitor=visitor,
            pass_id=GatePassService.generate_gate_pass_id(),
            valid_till=timezone.now() + timedelta(hours=valid_hours),
        )

    @staticmethod
    def is_gate_pass_valid(gate_pass):
        return gate_pass.status == 'approved' and timezone.now() < gate_pass.valid_till


class VisitorService:
    """Service for visitor management operations."""

    @staticmethod
    def get_visitor_statistics():
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
        from .models import VisitorHistory
        start_date = timezone.now() - timedelta(days=days)
        return VisitorHistory.objects.filter(
            visitor__resident=resident,
            created_at__gte=start_date,
        ).order_by('-created_at')

    @staticmethod
    def get_guard_visitor_statistics(guard):
        from .models import Visitor
        today = timezone.now().date()
        return {
            'total_registered': Visitor.objects.filter(registered_by=guard).count(),
            'today_registered': Visitor.objects.filter(registered_by=guard, entry_time__date=today).count(),
            'active_visitors': Visitor.objects.filter(registered_by=guard, exit_time__isnull=True).count(),
        }
