"""
DRF API views for the audit app (admin-only).
"""
import csv
from datetime import timedelta

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdmin

from .models import SystemAudit
from .serializers import SystemAuditSerializer, SystemAuditListSerializer
from .services import AuditService


class AuditDashboardView(APIView):
    """
    GET /api/v1/audit/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        stats = AuditService.get_audit_statistics()
        return Response({'success': True, 'data': stats})


class AuditLogListView(APIView):
    """
    GET /api/v1/audit/logs/
    Supports: ?action_type=, ?status=, ?user_id=, ?search=, ?start_date=, ?end_date=
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = SystemAudit.objects.select_related('user').order_by('-timestamp')

        action_type = request.query_params.get('action_type', '')
        audit_status = request.query_params.get('status', '')
        user_id = request.query_params.get('user_id', '')
        search = request.query_params.get('search', '').strip()
        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')

        if action_type:
            qs = qs.filter(action_type=action_type)
        if audit_status:
            qs = qs.filter(status=audit_status)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if search:
            qs = qs.filter(
                Q(description__icontains=search)
                | Q(user__username__icontains=search)
                | Q(ip_address__icontains=search)
            )
        if start_date:
            qs = qs.filter(timestamp__date__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__date__lte=end_date)

        serializer = SystemAuditListSerializer(qs[:200], many=True)
        return Response({'success': True, 'count': qs.count(), 'data': serializer.data})


class AuditLogDetailView(APIView):
    """
    GET /api/v1/audit/logs/<id>/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, activity_id):
        try:
            log = SystemAudit.objects.select_related('user').get(id=activity_id)
        except SystemAudit.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Activity not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SystemAuditSerializer(log)
        return Response({'success': True, 'data': serializer.data})


class AuditExportView(APIView):
    """
    GET /api/v1/audit/export/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Timestamp', 'User', 'Action Type', 'Description',
            'Target Model', 'Target ID', 'Status', 'IP Address',
        ])

        logs = SystemAudit.objects.select_related('user').order_by('-timestamp')

        # Optional date filters
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if start:
            logs = logs.filter(timestamp__date__gte=start)
        if end:
            logs = logs.filter(timestamp__date__lte=end)

        for log in logs:
            writer.writerow([
                log.id,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'System',
                log.get_action_type_display(),
                log.description,
                log.target_model or '',
                log.target_id or '',
                log.get_status_display(),
                log.ip_address or '',
            ])

        return response
