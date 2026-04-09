from django.contrib import admin
from .models import Visitor, OTP, GatePass, VisitorHistory


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    """Admin configuration for Visitor model - PROJECT REQUIREMENTS COMPLIANT"""
    list_display = ('visitor_name', 'mobile_number', 'resident', 'purpose', 'entry_time', 'created_at')
    list_filter = ('purpose', 'identity_proof', 'entry_time', 'created_at')
    search_fields = ('visitor_name', 'mobile_number', 'purpose', 'resident__user__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        (None, {'fields': ('visitor_name', 'mobile_number', 'purpose', 'resident')}),
        ('Identity', {'fields': ('identity_proof', 'identity_number', 'visitor_photo')}),
        ('Timing', {'fields': ('entry_time',)}),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Admin configuration for OTP model"""
    list_display = ('visitor', 'otp_code', 'is_verified', 'created_at', 'expires_at', 'attempts')
    list_filter = ('is_verified', 'created_at', 'expires_at')
    search_fields = ('visitor__visitor_name',)
    ordering = ('-created_at',)
    readonly_fields = ('otp_code', 'created_at', 'attempts')


@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    """Admin configuration for GatePass model"""
    list_display = ('pass_id', 'visitor', 'issue_time', 'valid_till', 'status', 'qr_code')
    list_filter = ('status', 'issue_time', 'valid_till')
    search_fields = ('pass_id', 'visitor__visitor_name')
    ordering = ('-issue_time',)
    readonly_fields = ('pass_id', 'issue_time', 'qr_code')


@admin.register(VisitorHistory)
class VisitorHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for VisitorHistory model"""
    list_display = ('visitor', 'entry_time', 'exit_time', 'purpose', 'status', 'created_at')
    list_filter = ('status', 'entry_time', 'created_at')
    search_fields = ('visitor__visitor_name', 'purpose')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
