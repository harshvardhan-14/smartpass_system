"""
DRF API views for the visitors app.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import AuditService
from core.permissions import IsSecurityGuard, IsSecurityGuardOrAdmin
from core.utils import generate_qr_code, log_activity
from accounts.models import Resident, SecurityGuard

from .models import Visitor, OTP, GatePass, VisitorHistory
from .serializers import (
    VisitorSerializer,
    VisitorListSerializer,
    VisitorRegistrationSerializer,
    OTPVerifySerializer,
    GatePassSerializer,
    ResidentSearchSerializer,
)
from .services import OTPService


# ─── Visitor Registration & Detail ─────────────────────────────────────────────

class VisitorListCreateView(APIView):
    """
    GET  /api/v1/visitors/          – List visitors (filtered by role)
    POST /api/v1/visitors/          – Register a new visitor (security guard only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        visitors = self._get_visitor_queryset(request)

        # Search
        search = request.query_params.get('search', '').strip()
        if search:
            visitors = visitors.filter(
                Q(visitor_name__icontains=search)
                | Q(mobile_number__icontains=search)
                | Q(purpose__icontains=search)
                | Q(resident__flat_number__icontains=search)
                | Q(resident__building_name__icontains=search)
                | Q(identity_number__icontains=search)
            )

        # Date filter
        date = request.query_params.get('date', '')
        if date:
            visitors = visitors.filter(created_at__date=date)

        # Status filter (via VisitorHistory)
        status_filter = request.query_params.get('status', '')
        if status_filter:
            ids = VisitorHistory.objects.filter(status=status_filter).values_list('visitor_id', flat=True)
            visitors = visitors.filter(id__in=ids)

        visitors = visitors.order_by('-created_at')
        serializer = VisitorListSerializer(visitors, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': visitors.count(),
            'data': serializer.data,
        })

    def post(self, request):
        # Only security guards can register visitors
        guard = getattr(request.user, 'securityguard', None)
        if not guard:
            return Response(
                {'success': False, 'message': 'Only security guards can register visitors.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = VisitorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        resident = Resident.objects.get(id=data['resident_id'])

        with transaction.atomic():
            visitor = Visitor.objects.create(
                visitor_name=data['visitor_name'],
                mobile_number=data['mobile_number'],
                purpose=data['purpose'],
                resident=resident,
                registered_by=guard,
                entry_time=timezone.now(),
                identity_proof=data.get('identity_proof', 'aadhar'),
                identity_number=data.get('identity_number', ''),
                visitor_photo=data.get('visitor_photo'),
            )

            # Generate and send OTP
            otp_code = OTPService.generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            OTP.objects.create(visitor=visitor, otp_code=otp_code, expires_at=expires_at)
            OTPService.send_otp(resident.phone_number, otp_code, resident.user.get_full_name())

            # Create history record
            VisitorHistory.objects.create(
                visitor=visitor,
                entry_time=visitor.entry_time,
                purpose=visitor.purpose,
                status='pending',
            )

        log_activity(guard.user, 'visitor_register', f'Visitor {visitor.visitor_name} registered', request)
        log_activity(guard.user, 'otp_generate', f'OTP generated for {visitor.visitor_name}', request)

        return Response(
            {
                'success': True,
                'message': 'Visitor registered. OTP sent to resident.',
                'visitor_id': visitor.id,
                'data': VisitorSerializer(visitor, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_visitor_queryset(request):
        user = request.user
        if user.user_type == 'resident':
            return Visitor.objects.filter(resident=user.resident)
        return Visitor.objects.all()


class VisitorDetailView(APIView):
    """
    GET /api/v1/visitors/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, visitor_id):
        visitor = self._get_visitor(request, visitor_id)
        if visitor is None:
            return Response(
                {'success': False, 'message': 'Visitor not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = VisitorSerializer(visitor, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    @staticmethod
    def _get_visitor(request, visitor_id):
        try:
            visitor = Visitor.objects.get(id=visitor_id)
        except Visitor.DoesNotExist:
            return None
        user = request.user
        if user.user_type == 'resident':
            if not hasattr(user, 'resident') or visitor.resident != user.resident:
                return None
        return visitor


class VerifyOTPView(APIView):
    """
    POST /api/v1/visitors/<id>/verify-otp/
    Security guard submits the OTP to approve entry.
    """
    permission_classes = [IsAuthenticated, IsSecurityGuardOrAdmin]

    def post(self, request, visitor_id):
        try:
            visitor = Visitor.objects.get(id=visitor_id)
        except Visitor.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Visitor not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            otp = visitor.otp
        except OTP.DoesNotExist:
            return Response(
                {'success': False, 'message': 'No OTP record for this visitor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entered_otp = serializer.validated_data['otp']

        if not otp.is_valid():
            # Mark history as rejected
            VisitorHistory.objects.filter(visitor=visitor, status='pending').update(status='rejected')
            GatePass.objects.filter(visitor=visitor, status='pending').update(status='rejected')
            return Response(
                {'success': False, 'message': 'OTP has expired or maximum attempts exceeded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp.verify_otp(entered_otp):
            remaining = max(0, 3 - otp.attempts)
            return Response(
                {
                    'success': False,
                    'message': f'Invalid OTP. {remaining} attempt(s) remaining.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP verified – create gate pass
        with transaction.atomic():
            valid_till = timezone.now() + timedelta(hours=24)
            gate_pass = GatePass.objects.create(
                visitor=visitor,
                valid_till=valid_till,
                status='approved',
            )
            qr_data = (
                f"Gate Pass ID: {gate_pass.pass_id}\n"
                f"Visitor: {visitor.visitor_name}\n"
                f"Resident: {visitor.resident.user.get_full_name()}\n"
                f"Flat: {visitor.resident.flat_number}"
            )
            gate_pass.qr_code = generate_qr_code(qr_data)
            gate_pass.save()

            VisitorHistory.objects.filter(visitor=visitor, status='pending').update(status='in_process')

        log_activity(request.user, 'otp_verify', f'OTP verified for {visitor.visitor_name}', request)
        log_activity(request.user, 'gate_pass_issue', f'Gate pass issued: {gate_pass.pass_id}', request)

        return Response({
            'success': True,
            'message': 'OTP verified. Gate pass issued.',
            'gate_pass': GatePassSerializer(gate_pass, context={'request': request}).data,
        })


class MarkExitView(APIView):
    """
    POST /api/v1/visitors/<id>/mark-exit/
    Security guard marks a visitor as exited.
    """
    permission_classes = [IsAuthenticated, IsSecurityGuardOrAdmin]

    def post(self, request, visitor_id):
        try:
            visitor = Visitor.objects.get(id=visitor_id)
        except Visitor.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Visitor not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if visitor.exit_time:
            return Response(
                {'success': False, 'message': 'Exit already recorded for this visitor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        with transaction.atomic():
            visitor.exit_time = now
            visitor.save(update_fields=['exit_time'])
            VisitorHistory.objects.filter(visitor=visitor).update(exit_time=now, status='completed')

        log_activity(request.user, 'visitor_exit', f'Visitor {visitor.visitor_name} marked exit', request)
        return Response({'success': True, 'message': f'Exit recorded for {visitor.visitor_name}.'})


# ─── Gate Passes ───────────────────────────────────────────────────────────────

class GatePassListView(APIView):
    """
    GET /api/v1/gate-passes/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type == 'resident':
            gate_passes = GatePass.objects.filter(visitor__resident=user.resident)
        else:
            gate_passes = GatePass.objects.all()

        gate_passes = gate_passes.select_related('visitor').order_by('-issue_time')
        serializer = GatePassSerializer(gate_passes, many=True, context={'request': request})
        return Response({'success': True, 'count': gate_passes.count(), 'data': serializer.data})


class GatePassDetailView(APIView):
    """
    GET /api/v1/gate-passes/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pass_id):
        try:
            gate_pass = GatePass.objects.select_related('visitor__resident__user').get(id=pass_id)
        except GatePass.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Gate pass not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        if user.user_type == 'resident':
            if not hasattr(user, 'resident') or gate_pass.visitor.resident != user.resident:
                return Response(
                    {'success': False, 'message': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = GatePassSerializer(gate_pass, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


# ─── Dashboard Stats ───────────────────────────────────────────────────────────

class VisitorDashboardView(APIView):
    """
    GET /api/v1/visitors/dashboard/
    Role-aware dashboard statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        if user.user_type == 'resident' and hasattr(user, 'resident'):
            data = self._resident_stats(user.resident, today)
        elif user.user_type in ('security', 'guard') and hasattr(user, 'securityguard'):
            data = self._guard_stats(user.securityguard, today)
        else:
            data = self._admin_stats(today)

        return Response({'success': True, 'data': data})

    @staticmethod
    def _resident_stats(resident, today):
        today_visitors = Visitor.objects.filter(resident=resident, entry_time__date=today)
        pending = Visitor.objects.filter(resident=resident, visitorhistory__status='pending')
        return {
            'today_count': today_visitors.count(),
            'pending_count': pending.count(),
            'total_count': Visitor.objects.filter(resident=resident).count(),
        }

    @staticmethod
    def _guard_stats(guard, today):
        today_registered = Visitor.objects.filter(registered_by=guard, entry_time__date=today)
        pending = Visitor.objects.filter(registered_by=guard, visitorhistory__status='pending')
        active = Visitor.objects.filter(registered_by=guard, exit_time__isnull=True, entry_time__date=today)
        return {
            'today_count': today_registered.count(),
            'pending_count': pending.count(),
            'active_count': active.count(),
            'total_registered': Visitor.objects.filter(registered_by=guard).count(),
        }

    @staticmethod
    def _admin_stats(today):
        return {
            'today_count': Visitor.objects.filter(entry_time__date=today).count(),
            'pending_count': VisitorHistory.objects.filter(status='pending').count(),
            'active_count': Visitor.objects.filter(exit_time__isnull=True, entry_time__date=today).count(),
            'total_count': Visitor.objects.count(),
            'approved_count': VisitorHistory.objects.filter(status='approved').count(),
            'rejected_count': VisitorHistory.objects.filter(status='rejected').count(),
        }


# ─── Visitor History ───────────────────────────────────────────────────────────

class VisitorHistoryView(APIView):
    """
    GET /api/v1/visitors/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.user_type == 'resident' and hasattr(user, 'resident'):
            qs = VisitorHistory.objects.filter(visitor__resident=user.resident)
        else:
            qs = VisitorHistory.objects.all()

        # Filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        hist_status = request.query_params.get('status')

        if start_date:
            qs = qs.filter(entry_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(entry_time__date__lte=end_date)
        if hist_status:
            qs = qs.filter(status=hist_status)

        qs = qs.select_related('visitor__resident__user').order_by('-created_at')

        from .serializers import VisitorHistorySerializer
        serializer = VisitorHistorySerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'data': serializer.data})


# ─── Resident Search ───────────────────────────────────────────────────────────

class ResidentSearchView(APIView):
    """
    GET /api/v1/visitors/search-residents/?q=<query>
    """
    permission_classes = [IsAuthenticated, IsSecurityGuardOrAdmin]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if query:
            residents = Resident.objects.filter(
                Q(flat_number__icontains=query)
                | Q(building_name__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
            )
        else:
            residents = Resident.objects.all()

        residents = (
            residents
            .select_related('user')
            .annotate(visitor_count=Count('visitors'))
            .order_by('-visitor_count', 'building_name', 'flat_number')[:20]
        )

        serializer = ResidentSearchSerializer(residents, many=True)
        return Response({'success': True, 'data': serializer.data})
