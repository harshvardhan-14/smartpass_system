"""
Template-based views for the dashboard app (admin-only).
"""
import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View

from accounts.decorators import admin_required
from accounts.models import CustomUser, Resident, SecurityGuard, Admin
from audit.models import SystemAudit
from visitors.models import Visitor, GatePass, VisitorHistory
from core.utils import log_activity

from .models import DashboardSettings


# ─── Admin Dashboard ──────────────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)

    context = {
        'total_residents': Resident.objects.count(),
        'total_guards': SecurityGuard.objects.count(),
        'total_visitors': Visitor.objects.count(),
        'today_visitors': Visitor.objects.filter(entry_time__date=today).count(),
        'week_visitors': Visitor.objects.filter(created_at__date__gte=seven_days_ago).count(),
        'pending_visitors': VisitorHistory.objects.filter(status='pending').count(),
        'approved_gate_passes': GatePass.objects.filter(status='approved').count(),
        'recent_activities': SystemAudit.objects.select_related('user').order_by('-timestamp')[:10],
        'recent_visitors': Visitor.objects.select_related('resident', 'registered_by').order_by('-created_at')[:5],
    }
    return render(request, 'admin_dashboard_enhanced.html', context)


# ─── User Management ──────────────────────────────────────────────────────────

@admin_required
def user_groups(request):
    context = {
        'residents': Resident.objects.select_related('user').all(),
        'guards': SecurityGuard.objects.select_related('user').all(),
        'admins': Admin.objects.select_related('user').all(),
        'total_residents': Resident.objects.count(),
        'total_guards': SecurityGuard.objects.count(),
        'total_admins': Admin.objects.count(),
    }
    return render(request, 'user_groups_enhanced.html', context)


@admin_required
def users_by_type(request, user_type):
    search = request.GET.get('search', '').strip()
    qs = CustomUser.objects.filter(user_type=user_type)
    if search:
        qs = qs.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )
    context = {
        'users': qs.order_by('-created_at'),
        'user_type': user_type,
        'search_query': search,
    }
    return render(request, 'users_by_type_enhanced.html', context)


# ─── Reports ──────────────────────────────────────────────────────────────────

@admin_required
def reports(request):
    return render(request, 'reports_enhanced.html')


@admin_required
def visitor_reports(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    qs = Visitor.objects.all()
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    by_status = list(
        VisitorHistory.objects.filter(visitor__in=qs)
        .values('status').annotate(count=Count('id'))
    )
    by_purpose = list(qs.values('purpose').annotate(count=Count('id')).order_by('-count')[:10])

    context = {
        'total': qs.count(),
        'by_status': by_status,
        'by_purpose': by_purpose,
        'start_date': start,
        'end_date': end,
    }
    return render(request, 'visitor_reports_enhanced.html', context)


@admin_required
def activity_reports(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    qs = SystemAudit.objects.all()
    if start:
        qs = qs.filter(timestamp__date__gte=start)
    if end:
        qs = qs.filter(timestamp__date__lte=end)

    by_action = list(qs.values('action_type').annotate(count=Count('id')).order_by('-count'))
    context = {
        'total': qs.count(),
        'by_action': by_action,
        'start_date': start,
        'end_date': end,
    }
    return render(request, 'activity_reports_enhanced.html', context)


@admin_required
def gate_pass_reports(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    qs = GatePass.objects.all()
    if start:
        qs = qs.filter(issue_time__date__gte=start)
    if end:
        qs = qs.filter(issue_time__date__lte=end)

    by_status = list(qs.values('status').annotate(count=Count('id')))
    context = {
        'total': qs.count(),
        'by_status': by_status,
        'gate_passes': qs.select_related('visitor').order_by('-issue_time')[:50],
        'start_date': start,
        'end_date': end,
    }
    return render(request, 'gate_pass_reports_enhanced.html', context)


@admin_required
def export_reports(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="visitors_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Visitor Name', 'Mobile', 'Purpose',
        'Resident Flat', 'Building', 'Entry Time', 'Exit Time',
        'Identity Proof', 'Status', 'Registered By', 'Created At',
    ])

    for v in Visitor.objects.select_related('resident', 'registered_by__user').prefetch_related('visitorhistory').order_by('-created_at'):
        history = v.visitorhistory.order_by('-created_at').first()
        writer.writerow([
            v.id, v.visitor_name, v.mobile_number, v.purpose,
            v.resident.flat_number if v.resident else '',
            v.resident.building_name if v.resident else '',
            v.entry_time.strftime('%Y-%m-%d %H:%M') if v.entry_time else '',
            v.exit_time.strftime('%Y-%m-%d %H:%M') if v.exit_time else '',
            v.get_identity_proof_display(),
            history.status if history else '',
            v.registered_by.user.get_full_name() if v.registered_by and v.registered_by.user else '',
            v.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    log_activity(request.user, 'data_export', 'Visitor report exported', request)
    return response


# ─── Settings ─────────────────────────────────────────────────────────────────

@admin_required
def dashboard_settings(request):
    settings_obj = DashboardSettings.get_settings()

    if request.method == 'POST':
        settings_obj.otp_expiry_minutes = int(request.POST.get('otp_expiry_minutes', settings_obj.otp_expiry_minutes))
        settings_obj.max_otp_attempts = int(request.POST.get('max_otp_attempts', settings_obj.max_otp_attempts))
        settings_obj.enable_notifications = request.POST.get('enable_notifications') == 'on'
        settings_obj.auto_cleanup_days = int(request.POST.get('auto_cleanup_days', settings_obj.auto_cleanup_days))
        settings_obj.items_per_page = int(request.POST.get('items_per_page', settings_obj.items_per_page))
        settings_obj.save()
        log_activity(request.user, 'config_change', 'Dashboard settings updated', request)
        messages.success(request, 'Settings saved successfully.')
        return redirect('dashboard:dashboard_settings')

    return render(request, 'settings.html', {'settings': settings_obj})


# ─── Inline JSON API endpoints (used by dashboard JS) ─────────────────────────

class VisitorDetailAPI(View):
    def get(self, request, visitor_id):
        if not request.user.is_authenticated or request.user.user_type != 'admin':
            return JsonResponse({'error': 'Forbidden'}, status=403)
        visitor = get_object_or_404(Visitor, id=visitor_id)
        history = VisitorHistory.objects.filter(visitor=visitor).first()
        return JsonResponse({
            'id': visitor.id,
            'visitor_name': visitor.visitor_name,
            'mobile_number': visitor.mobile_number,
            'purpose': visitor.purpose,
            'entry_time': visitor.entry_time.strftime('%Y-%m-%d %H:%M') if visitor.entry_time else None,
            'exit_time': visitor.exit_time.strftime('%Y-%m-%d %H:%M') if visitor.exit_time else None,
            'resident_flat': visitor.resident.flat_number if visitor.resident else '',
            'status': history.status if history else 'unknown',
        })


class UserDetailAPI(View):
    def get(self, request, user_id):
        if not request.user.is_authenticated or request.user.user_type != 'admin':
            return JsonResponse({'error': 'Forbidden'}, status=403)
        user = get_object_or_404(CustomUser, id=user_id)
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'user_type': user.user_type,
            'phone_number': user.phone_number or '',
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d'),
        })
