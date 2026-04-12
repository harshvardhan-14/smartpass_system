"""
DRF API views for the dashboard app (admin-only).
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

from accounts.models import CustomUser, Resident, SecurityGuard, Admin
from audit.models import SystemAudit
from core.permissions import IsAdmin
from visitors.models import Visitor, GatePass, VisitorHistory

from .models import DashboardSettings
from .serializers import DashboardSettingsSerializer, UserSummarySerializer


# ─── Admin Dashboard Stats ─────────────────────────────────────────────────────

class AdminDashboardView(APIView):
    """
    GET /api/v1/dashboard/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)

        data = {
            'users': {
                'total': CustomUser.objects.count(),
                'residents': Resident.objects.count(),
                'guards': SecurityGuard.objects.count(),
                'admins': Admin.objects.count(),
            },
            'visitors': {
                'total': Visitor.objects.count(),
                'today': Visitor.objects.filter(entry_time__date=today).count(),
                'this_week': Visitor.objects.filter(created_at__date__gte=seven_days_ago).count(),
                'pending': VisitorHistory.objects.filter(status='pending').count(),
                'active': Visitor.objects.filter(exit_time__isnull=True, entry_time__isnull=False).count(),
            },
            'gate_passes': {
                'total': GatePass.objects.count(),
                'approved': GatePass.objects.filter(status='approved').count(),
                'rejected': GatePass.objects.filter(status='rejected').count(),
                'pending': GatePass.objects.filter(status='pending').count(),
            },
            'audit': {
                'total_activities': SystemAudit.objects.count(),
                'today_activities': SystemAudit.objects.filter(timestamp__date=today).count(),
                'security_events': SystemAudit.objects.filter(
                    action_type__in=['security_breach', 'system_error']
                ).count(),
            },
        }
        return Response({'success': True, 'data': data})


# ─── User Management ───────────────────────────────────────────────────────────

class UserListView(APIView):
    """
    GET /api/v1/dashboard/users/           – All users
    GET /api/v1/dashboard/users/?type=...  – Filter by type
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        user_type = request.query_params.get('type', '')
        search = request.query_params.get('search', '').strip()

        qs = CustomUser.objects.all()
        if user_type in ('admin', 'resident', 'security', 'guard'):
            qs = qs.filter(user_type=user_type)
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        qs = qs.order_by('-created_at')
        serializer = UserSummarySerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'data': serializer.data})


class UserDetailAdminView(APIView):
    """
    GET    /api/v1/dashboard/users/<user_id>/
    PATCH  /api/v1/dashboard/users/<user_id>/
    DELETE /api/v1/dashboard/users/<user_id>/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': UserSummarySerializer(user).data})

    def patch(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        allowed = ['first_name', 'last_name', 'email', 'phone_number', 'is_active']
        for field in allowed:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response({'success': True, 'message': 'User updated.', 'data': UserSummarySerializer(user).data})

    def delete(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if user == request.user:
            return Response(
                {'success': False, 'message': 'Cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        username = user.username
        user.delete()
        return Response({'success': True, 'message': f'User {username} deleted.'})

    @staticmethod
    def _get_user(user_id):
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return None


# ─── Reports ──────────────────────────────────────────────────────────────────

class VisitorReportsView(APIView):
    """
    GET /api/v1/dashboard/reports/visitors/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        qs = Visitor.objects.all()
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)

        total = qs.count()
        by_status = list(
            VisitorHistory.objects.filter(visitor__in=qs)
            .values('status')
            .annotate(count=Count('id'))
        )
        by_purpose = list(
            qs.values('purpose').annotate(count=Count('id')).order_by('-count')[:10]
        )
        by_day = list(
            qs.extra(select={'day': 'DATE(created_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        return Response({
            'success': True,
            'data': {
                'total': total,
                'by_status': by_status,
                'by_purpose': by_purpose,
                'by_day': by_day,
            },
        })


class ActivityReportsView(APIView):
    """
    GET /api/v1/dashboard/reports/activity/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        qs = SystemAudit.objects.all()
        if start:
            qs = qs.filter(timestamp__date__gte=start)
        if end:
            qs = qs.filter(timestamp__date__lte=end)

        by_action = list(qs.values('action_type').annotate(count=Count('id')).order_by('-count'))
        by_status = list(qs.values('status').annotate(count=Count('id')))

        return Response({
            'success': True,
            'data': {
                'total': qs.count(),
                'by_action': by_action,
                'by_status': by_status,
            },
        })


class GatePassReportsView(APIView):
    """
    GET /api/v1/dashboard/reports/gate-passes/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = GatePass.objects.all()
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if start:
            qs = qs.filter(issue_time__date__gte=start)
        if end:
            qs = qs.filter(issue_time__date__lte=end)

        by_status = list(qs.values('status').annotate(count=Count('id')))
        return Response({
            'success': True,
            'data': {
                'total': qs.count(),
                'by_status': by_status,
            },
        })


class ExportReportsView(APIView):
    """
    GET /api/v1/dashboard/reports/export/
    Exports visitor data as CSV.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visitors_report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Visitor Name', 'Mobile', 'Purpose',
            'Resident Flat', 'Building', 'Entry Time', 'Exit Time',
            'Identity Proof', 'Status', 'Registered By', 'Created At',
        ])

        visitors = Visitor.objects.select_related(
            'resident', 'registered_by__user'
        ).prefetch_related('visitorhistory').order_by('-created_at')

        for v in visitors:
            history = v.visitorhistory.order_by('-created_at').first()
            writer.writerow([
                v.id,
                v.visitor_name,
                v.mobile_number,
                v.purpose,
                v.resident.flat_number if v.resident else '',
                v.resident.building_name if v.resident else '',
                v.entry_time.strftime('%Y-%m-%d %H:%M') if v.entry_time else '',
                v.exit_time.strftime('%Y-%m-%d %H:%M') if v.exit_time else '',
                v.get_identity_proof_display(),
                history.status if history else '',
                v.registered_by.user.get_full_name() if v.registered_by and v.registered_by.user else '',
                v.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response


# ─── Settings ─────────────────────────────────────────────────────────────────

class DashboardSettingsView(APIView):
    """
    GET   /api/v1/dashboard/settings/
    PATCH /api/v1/dashboard/settings/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        settings_obj = DashboardSettings.get_settings()
        serializer = DashboardSettingsSerializer(settings_obj)
        return Response({'success': True, 'data': serializer.data})

    def patch(self, request):
        settings_obj = DashboardSettings.get_settings()
        serializer = DashboardSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Settings updated.', 'data': serializer.data})
