from django.contrib import admin
from .models import SystemAudit


@admin.register(SystemAudit)
class SystemAuditAdmin(admin.ModelAdmin):
    """Admin configuration for SystemAudit model"""
    list_display = ('user', 'action_type', 'description', 'target_model', 'target_id', 'status', 'timestamp', 'ip_address')
    list_filter = ('action_type', 'status', 'timestamp', 'target_model')
    search_fields = ('user__username', 'description', 'target_model')
    ordering = ('-timestamp',)
    readonly_fields = ('user', 'action_type', 'description', 'target_model', 'target_id', 'old_values', 'new_values', 'status', 'ip_address', 'user_agent', 'timestamp')
    
    def has_add_permission(self, request):
        return False  # Manual audit logging only
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be editable
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete audit logs
