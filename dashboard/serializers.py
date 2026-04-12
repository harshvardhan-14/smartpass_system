"""
Serializers for the dashboard app.
"""
from rest_framework import serializers
from .models import DashboardSettings
from accounts.models import CustomUser, Resident, SecurityGuard, Admin


class DashboardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardSettings
        fields = [
            'otp_expiry_minutes',
            'max_otp_attempts',
            'enable_notifications',
            'auto_cleanup_days',
            'items_per_page',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_info = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'full_name',
            'user_type', 'phone_number', 'is_active',
            'created_at', 'profile_info',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_profile_info(self, obj):
        if obj.user_type == 'resident':
            profile = getattr(obj, 'resident', None)
            if profile:
                return {'flat_number': profile.flat_number, 'building_name': profile.building_name}
        elif obj.user_type in ('security', 'guard'):
            profile = getattr(obj, 'securityguard', None)
            if profile:
                return {'employee_id': profile.employee_id, 'shift': profile.shift}
        elif obj.user_type == 'admin':
            profile = getattr(obj, 'admin', None)
            if profile:
                return {'admin_id': profile.admin_id, 'department': profile.department}
        return None
