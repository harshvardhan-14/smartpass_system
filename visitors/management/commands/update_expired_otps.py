from django.core.management.base import BaseCommand
from django.utils import timezone
from visitors.models import OTP, VisitorHistory, GatePass


class Command(BaseCommand):
    help = 'Update expired OTPs to rejected status'

    def handle(self, *args, **options):
        current_time = timezone.now()
        expired_otps = OTP.objects.filter(
            expires_at__lt=current_time,
            is_verified=False
        )
        
        self.stdout.write(f"🔍 Checking expired OTPs at {current_time}")
        self.stdout.write(f"📊 Found {expired_otps.count()} expired OTPs")
        
        updated_count = 0
        
        for otp in expired_otps:
            self.stdout.write(f"⏰ OTP for {otp.visitor.visitor_name} expired at {otp.expires_at}")
            try:
                history = VisitorHistory.objects.get(visitor=otp.visitor)
                if history.status == 'pending':
                    history.status = 'rejected'
                    history.save()
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"❌ Updated status to 'rejected' for {otp.visitor.visitor_name}"))
                    
                    # Also update gate pass status if exists
                    gate_pass = GatePass.objects.filter(visitor=otp.visitor).first()
                    if gate_pass and gate_pass.status == 'pending':
                        gate_pass.status = 'rejected'
                        gate_pass.save()
            except VisitorHistory.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"⚠️ No history found for {otp.visitor.visitor_name}"))
        
        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} expired OTPs to 'rejected' status"))
