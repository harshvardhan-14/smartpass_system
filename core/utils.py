"""
Core utilities for Smart Gate Pass System
"""
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import qrcode
import io
from django.core.files.base import ContentFile


def generate_otp(length=6):
    """Generate random OTP"""
    return ''.join(random.choices(string.digits, k=length))


def generate_unique_id(prefix, length=8):
    """Generate unique ID with prefix"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}{timestamp}{random_str}"


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_qr_code(data, save_path=None):
    """Generate QR code for given data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    if save_path:
        img.save(save_path)
    else:
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue(), name='qr_code.png')


def format_duration(duration):
    """Format duration in human readable format"""
    if not duration:
        return "-"
    
    total_seconds = duration.total_seconds()
    if total_seconds < 60:
        return f"{int(total_seconds)}s"
    elif total_seconds < 3600:
        return f"{int(total_seconds // 60)}m"
    else:
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def validate_phone_number(phone):
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove any non-digit characters
    phone_digits = ''.join(filter(str.isdigit, phone))
    
    # Check if it's 10 digits (Indian mobile number)
    return len(phone_digits) == 10 and phone_digits.isdigit()


def send_sms(phone_number, message):
    """Send SMS via Twilio"""
    from django.conf import settings
    
    # Try to send via Twilio if configured
    if (hasattr(settings, 'TWILIO_ACCOUNT_SID') and 
        settings.TWILIO_ACCOUNT_SID and 
        settings.TWILIO_AUTH_TOKEN and 
        settings.TWILIO_PHONE_NUMBER):
        
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            twilio_message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=f"+91{phone_number}"
            )
            
            print(f"SMS sent successfully via Twilio")
            print(f"   Message SID: {twilio_message.sid}")
            print(f"   To: +91{phone_number}")
            print(f"   Message: {message}")
            return True
            
        except Exception as e:
            print(f"Twilio SMS failed: {e}")
            print(f"Falling back to console output:")
            print(f"   To: {phone_number}")
            print(f"   Message: {message}")
            return False
    else:
        # Fallback to console if Twilio not configured
        print(f"SMS to {phone_number}: {message}")
        print(f"Twilio not configured - using console output")
        return True


def log_activity(user, action, description="", request=None, target_id=None):
    """Log system activity (helper function)"""
    from audit.models import SystemAudit
    
    SystemAudit.objects.create(
        user=user,
        action_type=action,
        description=description,
        target_id=target_id,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
    )
