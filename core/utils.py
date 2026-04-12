"""
Core utilities for Smart Gate Pass System.
"""
import logging
import random
import string
from datetime import datetime

import qrcode
import io
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def generate_unique_id(prefix, length=8):
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f'{prefix}{timestamp}{random_str}'


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def generate_qr_code(data, save_path=None):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    if save_path:
        img.save(save_path)
        return save_path
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name='qr_code.png')


def format_duration(duration):
    if not duration:
        return '-'
    total_seconds = duration.total_seconds()
    if total_seconds < 60:
        return f'{int(total_seconds)}s'
    if total_seconds < 3600:
        return f'{int(total_seconds // 60)}m'
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f'{hours}h {minutes}m'


def validate_phone_number(phone):
    if not phone:
        return False
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) == 10


def send_sms(phone_number, message):
    """Send SMS via Twilio, falling back to log output when unconfigured."""
    if (
        getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        and getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        and getattr(settings, 'TWILIO_PHONE_NUMBER', '')
    ):
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            twilio_message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=f'+91{phone_number}',
            )
            logger.info('SMS sent via Twilio. SID=%s To=+91%s', twilio_message.sid, phone_number)
            return True
        except Exception as exc:
            logger.error('Twilio SMS failed: %s', exc)
            return False

    logger.warning('SMS (dev-mode): phone=%s message=%s', phone_number, message)
    return True


def log_activity(user, action, description='', request=None, target_id=None):
    """Log system activity to the audit table."""
    from audit.models import SystemAudit
    SystemAudit.objects.create(
        user=user,
        action_type=action,
        description=description,
        target_id=target_id,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
    )
