"""
Template-based views for the audit app (admin-only).
"""
import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from accounts.decorators import admin_required
from core.utils import log_activity

from .models import SystemAudit
from .services import AuditService


@admin_required
def audit_dashboard(request):
    stats = AuditService.get_audit_statistics()
    recent = AuditService.get_recent_activities(limit=10)
    return render(request, 'audit_logs.html', {
        'stats': stats,
        'recent_activities': recent,
    })


@admin_required
def audit_logs(request):
    qs = SystemAudit.objects.select_related('user').order_by('-timestamp')

    search = request.GET.get('search', '').strip()
    action_type = request.GET.get('action_type', '')
    audit_status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    if search:
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(user__username__icontains=search)
            | Q(ip_address__icontains=search)
        )
    if action_type:
        qs = qs.filter(action_type=action_type)
    if audit_status:
        qs = qs.filter(status=audit_status)
    if start_date:
        qs = qs.filter(timestamp__date__gte=start_date)
    if end_date:
        qs = qs.filter(timestamp__date__lte=end_date)

    return render(request, 'audit_logs.html', {
        'logs': qs[:200],
        'total': qs.count(),
        'action_types': SystemAudit.ACTION_TYPES,
        'status_types': SystemAudit.STATUS_TYPES,
        'search_query': search,
        'selected_action': action_type,
        'selected_status': audit_status,
        'start_date': start_date,
        'end_date': end_date,
    })


@admin_required
def audit_logs_by_type(request, action_type):
    qs = SystemAudit.objects.filter(action_type=action_type).select_related('user').order_by('-timestamp')
    return render(request, 'audit_logs.html', {
        'logs': qs[:200],
        'total': qs.count(),
        'action_types': SystemAudit.ACTION_TYPES,
        'selected_action': action_type,
    })


@admin_required
def search_audit_logs(request):
    query = request.GET.get('q', '').strip()
    qs = SystemAudit.objects.select_related('user').order_by('-timestamp')
    if query:
        qs = qs.filter(
            Q(description__icontains=query)
            | Q(user__username__icontains=query)
        )
    return render(request, 'audit_logs.html', {
        'logs': qs[:200],
        'total': qs.count(),
        'search_query': query,
        'action_types': SystemAudit.ACTION_TYPES,
    })


@admin_required
def export_audit_data(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Timestamp', 'User', 'Action', 'Description', 'Status', 'IP Address'])

    qs = SystemAudit.objects.select_related('user').order_by('-timestamp')
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    if start:
        qs = qs.filter(timestamp__date__gte=start)
    if end:
        qs = qs.filter(timestamp__date__lte=end)

    for log in qs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'System',
            log.get_action_type_display(),
            log.description,
            log.get_status_display(),
            log.ip_address or '',
        ])

    log_activity(request.user, 'data_export', 'Audit log exported', request)
    return response


# ─── Inline JSON (used by dashboard JS) ───────────────────────────────────────

@login_required(login_url='accounts:login')
def activity_details_api(request, activity_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Forbidden'}, status=403)
    log = get_object_or_404(SystemAudit, id=activity_id)
    return JsonResponse({
        'id': log.id,
        'action_type': log.get_action_type_display(),
        'description': log.description,
        'status': log.get_status_display(),
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'user': log.user.username if log.user else 'System',
        'ip_address': log.ip_address or '',
        'target_model': log.target_model or '',
        'target_id': log.target_id,
        'old_values': log.old_values,
        'new_values': log.new_values,
    })
