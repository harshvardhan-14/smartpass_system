"""
DRF API views for the accounts app.
"""
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from core.utils import generate_otp, send_sms, log_activity
from .models import CustomUser, Resident, SecurityGuard, Admin, PasswordResetOTP
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    ResidentRegistrationSerializer,
    SecurityGuardRegistrationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ResidentProfileUpdateSerializer,
    SecurityGuardProfileUpdateSerializer,
)


# ─── Auth ──────────────────────────────────────────────────────────────────────

class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh JWT tokens with user info.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {
                'success': True,
                'message': 'Login successful.',
                **response.data,
            }
            # Log login (user resolved from token data)
            try:
                username = request.data.get('username', '')
                user = CustomUser.objects.filter(username=username).first()
                if user:
                    log_activity(user, 'user_login', f'User {user.username} logged in via API', request)
            except Exception:
                pass
        return response


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'success': False, 'message': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_activity(request.user, 'user_logout', f'User {request.user.username} logged out', request)
            return Response({'success': True, 'message': 'Logged out successfully.'})
        except TokenError:
            return Response(
                {'success': False, 'message': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Send OTP to the user's registered phone number.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data['mobile_number']

        user = (
            CustomUser.objects.filter(phone_number=mobile, user_type__in=['resident', 'security']).first()
            or _find_user_by_profile_phone(mobile)
        )

        if not user:
            # Generic message to avoid user enumeration
            return Response({
                'success': True,
                'message': 'If an account with this number exists, an OTP has been sent.',
            })

        otp_code = generate_otp()
        PasswordResetOTP.objects.create(user=user, otp=otp_code)
        send_sms(user.phone_number or mobile, f'Your password reset OTP is: {otp_code}. Valid for 10 minutes.')

        return Response({
            'success': True,
            'message': 'OTP sent to registered mobile number.',
            'user_id': user.id,
        })


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/<user_id>/
    Verify OTP and set new password.
    """
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id, user_type__in=['resident', 'security'])
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'message': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_code = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        reset_otp = PasswordResetOTP.objects.filter(user=user, otp=otp_code, is_used=False).first()
        if not reset_otp or not reset_otp.is_valid():
            return Response(
                {'success': False, 'message': 'Invalid or expired OTP.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(new_password)
            user.save()
            reset_otp.is_used = True
            reset_otp.save()

        log_activity(user, 'user_update', f'Password reset for {user.username}', request)
        return Response({'success': True, 'message': 'Password reset successful. Please login.'})


# ─── Registration ──────────────────────────────────────────────────────────────

class RegisterResidentView(APIView):
    """
    POST /api/v1/accounts/register/resident/
    """
    permission_classes = [AllowAny]
    parser_classes_override = None  # uses default (JSON + multipart)

    def post(self, request):
        serializer = ResidentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        log_activity(user, 'user_create', f'Resident {user.username} registered', request)
        return Response(
            {
                'success': True,
                'message': 'Resident registered successfully.',
                'user_id': user.id,
                'username': user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterSecurityGuardView(APIView):
    """
    POST /api/v1/accounts/register/guard/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SecurityGuardRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        log_activity(user, 'user_create', f'Security Guard {user.username} registered', request)
        return Response(
            {
                'success': True,
                'message': 'Security guard registered successfully.',
                'user_id': user.id,
                'username': user.username,
                'employee_id': getattr(user, '_employee_id', None),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── Profile ───────────────────────────────────────────────────────────────────

class MeView(APIView):
    """
    GET /api/v1/accounts/me/
    Returns full profile for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})


class ProfileView(APIView):
    """
    GET  /api/v1/accounts/profile/   – Retrieve profile
    PATCH /api/v1/accounts/profile/  – Update profile
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, serializer_class = self._get_profile_and_serializer(request.user)
        if profile is None:
            return Response({'success': True, 'data': UserSerializer(request.user).data})
        return Response({'success': True, 'data': serializer_class(profile).data})

    def patch(self, request):
        profile, serializer_class = self._get_profile_and_serializer(request.user)
        if profile is None:
            return Response(
                {'success': False, 'message': 'Profile not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = serializer_class(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Profile updated.', 'data': serializer.data})

    @staticmethod
    def _get_profile_and_serializer(user):
        if user.user_type == 'resident':
            profile = getattr(user, 'resident', None)
            return profile, ResidentProfileUpdateSerializer
        if user.user_type in ('security', 'guard'):
            profile = getattr(user, 'securityguard', None)
            return profile, SecurityGuardProfileUpdateSerializer
        return None, None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_user_by_profile_phone(mobile):
    """Search Resident and SecurityGuard profile tables for a matching phone."""
    resident = Resident.objects.filter(phone_number=mobile).first()
    if resident and resident.user:
        return resident.user
    guard = SecurityGuard.objects.filter(phone_number=mobile).first()
    if guard and guard.user:
        return guard.user
    return None
