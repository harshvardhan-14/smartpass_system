"""
Serializers for the visitors app.
"""
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Resident, SecurityGuard
from .models import Visitor, OTP, GatePass, VisitorHistory


class ResidentMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = ['id', 'full_name', 'flat_number', 'building_name', 'phone_number']

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else ''


class OTPSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = OTP
        fields = ['id', 'is_verified', 'created_at', 'expires_at', 'attempts', 'is_valid']
        read_only_fields = fields

    def get_is_valid(self, obj):
        return obj.is_valid()


class GatePassSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = GatePass
        fields = ['id', 'pass_id', 'issue_time', 'valid_till', 'status', 'qr_code', 'is_valid']
        read_only_fields = fields

    def get_is_valid(self, obj):
        return obj.is_valid()


class VisitorHistorySerializer(serializers.ModelSerializer):
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = VisitorHistory
        fields = ['id', 'entry_time', 'exit_time', 'purpose', 'status', 'created_at', 'duration_display']
        read_only_fields = fields

    def get_duration_display(self, obj):
        return obj.get_duration_display()


class VisitorSerializer(serializers.ModelSerializer):
    resident = ResidentMinimalSerializer(read_only=True)
    otp = OTPSerializer(read_only=True)
    gatepass = GatePassSerializer(read_only=True)
    history = serializers.SerializerMethodField()
    registered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Visitor
        fields = [
            'id', 'visitor_name', 'mobile_number', 'purpose',
            'resident', 'registered_by_name',
            'entry_time', 'exit_time',
            'identity_proof', 'identity_number',
            'visitor_photo', 'created_at',
            'otp', 'gatepass', 'history',
        ]
        read_only_fields = ['id', 'entry_time', 'exit_time', 'created_at']

    def get_history(self, obj):
        qs = obj.visitorhistory.order_by('-created_at').first()
        return VisitorHistorySerializer(qs).data if qs else None

    def get_registered_by_name(self, obj):
        if obj.registered_by and obj.registered_by.user:
            return obj.registered_by.user.get_full_name()
        return None


class VisitorListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    resident_flat = serializers.CharField(source='resident.flat_number', read_only=True)
    resident_building = serializers.CharField(source='resident.building_name', read_only=True)
    resident_name = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()

    class Meta:
        model = Visitor
        fields = [
            'id', 'visitor_name', 'mobile_number', 'purpose',
            'resident_flat', 'resident_building', 'resident_name',
            'entry_time', 'exit_time', 'created_at',
            'identity_proof', 'current_status',
        ]

    def get_resident_name(self, obj):
        if obj.resident and obj.resident.user:
            return obj.resident.user.get_full_name()
        return ''

    def get_current_status(self, obj):
        history = obj.visitorhistory.order_by('-created_at').first()
        return history.status if history else 'unknown'


class VisitorRegistrationSerializer(serializers.Serializer):
    resident_id = serializers.IntegerField()
    visitor_name = serializers.CharField(max_length=100)
    mobile_number = serializers.CharField(max_length=10)
    purpose = serializers.CharField(max_length=200)
    identity_proof = serializers.ChoiceField(
        choices=['aadhar', 'passport', 'license', 'others'],
        default='aadhar',
    )
    identity_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    visitor_photo = serializers.ImageField(required=False, allow_null=True)

    def validate_resident_id(self, value):
        if not Resident.objects.filter(id=value).exists():
            raise serializers.ValidationError('Resident not found.')
        return value

    def validate_mobile_number(self, value):
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) != 10:
            raise serializers.ValidationError('Mobile number must be exactly 10 digits.')
        return digits

    def validate_visitor_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Visitor name must be at least 3 characters.')
        return value.strip()


class OTPVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('OTP must contain only digits.')
        return value


class ResidentSearchSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    total_visitors = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = ['id', 'full_name', 'flat_number', 'building_name', 'phone_number', 'display_name', 'total_visitors']

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else ''

    def get_display_name(self, obj):
        return f"{obj.building_name or 'N/A'} - {obj.flat_number}"

    def get_total_visitors(self, obj):
        return obj.visitors.count()
