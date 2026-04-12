"""
Serializers for the audit app.
"""
from rest_framework import serializers
from .models import SystemAudit


class SystemAuditSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = SystemAudit
        fields = [
            'id', 'action_type', 'action_display',
            'description', 'target_model', 'target_id',
            'old_values', 'new_values',
            'status', 'status_display',
            'ip_address', 'user_agent',
            'timestamp', 'username',
        ]
        read_only_fields = fields

    def get_username(self, obj):
        return obj.user.username if obj.user else 'System'

    def get_action_display(self, obj):
        return obj.get_action_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()


class SystemAuditListSerializer(serializers.ModelSerializer):
    """Lightweight version for list views."""
    username = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()

    class Meta:
        model = SystemAudit
        fields = ['id', 'action_type', 'action_display', 'description', 'status', 'timestamp', 'username']

    def get_username(self, obj):
        return obj.user.username if obj.user else 'System'

    def get_action_display(self, obj):
        return obj.get_action_type_display()
