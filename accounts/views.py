"""
Template-based views for the accounts app.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from core.utils import generate_otp, send_sms, log_activity
from .models import CustomUser, Resident, SecurityGuard, Admin, PasswordResetOTP
from .forms import (
    ResidentRegistrationForm,
    SecurityGuardRegistrationForm,
    generate_employee_id,
    ForgotPasswordForm,
    ResetPasswordForm,
)


def home(request):
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('dashboard:admin_dashboard')
        elif request.user.user_type in ('resident', 'security', 'guard'):
            return redirect('visitors:visitor_dashboard')
    return render(request, 'home.html')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            log_activity(user, 'user_login', f'User {user.username} logged in', request)
            if user.user_type == 'admin':
                return redirect('dashboard:admin_dashboard')
            return redirect('visitors:visitor_dashboard')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def user_logout(request):
    if request.user.is_authenticated:
        log_activity(request.user, 'user_logout', f'User {request.user.username} logged out', request)
        logout(request)
    return redirect('accounts:login')


def register_resident(request):
    if request.method == 'POST':
        form = ResidentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    user_type='resident',
                    phone_number=form.cleaned_data['phone_number'],
                )
                Resident.objects.create(
                    user=user,
                    flat_number=form.cleaned_data['flat_number'],
                    building_name=form.cleaned_data.get('building_name', 'Building A'),
                    phone_number=form.cleaned_data['phone_number'],
                    profile_photo=form.cleaned_data.get('profile_photo'),
                )
            log_activity(user, 'user_create', f'Resident {user.username} registered', request)
            messages.success(request, 'Registration successful! Please login.')
            return redirect('accounts:login')
    else:
        form = ResidentRegistrationForm()

    return render(request, 'register_resident.html', {'form': form})


def register_security_guard(request):
    if request.method == 'POST':
        form = SecurityGuardRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    user_type='security',
                    phone_number=form.cleaned_data['phone_number'],
                )
                employee_id = None
                for _ in range(10):
                    eid = generate_employee_id()
                    if not SecurityGuard.objects.filter(employee_id=eid).exists():
                        employee_id = eid
                        break
                if not employee_id:
                    user.delete()
                    messages.error(request, 'Could not generate a unique Employee ID. Please try again.')
                    return render(request, 'register_guard.html', {'form': form})

                SecurityGuard.objects.create(
                    user=user,
                    employee_id=employee_id,
                    phone_number=form.cleaned_data['phone_number'],
                    shift=form.cleaned_data.get('shift', 'morning'),
                    profile_photo=form.cleaned_data.get('profile_photo'),
                )
            log_activity(user, 'user_create', f'Security Guard {user.username} registered', request)
            messages.success(request, f'Registration successful! Your Employee ID is: {employee_id}. Please login.')
            return redirect('accounts:login')
    else:
        form = SecurityGuardRegistrationForm()

    return render(request, 'register_guard.html', {'form': form})


@login_required(login_url='accounts:login')
def user_profile(request):
    try:
        if request.user.user_type == 'resident':
            profile = request.user.resident
        elif request.user.user_type in ('security', 'guard'):
            profile = request.user.securityguard
        elif request.user.user_type == 'admin':
            profile = request.user.admin
        else:
            profile = None
        return render(request, 'profile.html', {'profile': profile})
    except Exception:
        messages.error(request, 'Profile not found.')
        return redirect('home')


@login_required(login_url='accounts:login')
def edit_profile(request):
    try:
        if request.user.user_type == 'resident':
            profile = request.user.resident
        elif request.user.user_type in ('security', 'guard'):
            profile = request.user.securityguard
        elif request.user.user_type == 'admin':
            profile = request.user.admin
        else:
            profile = None
    except Exception:
        messages.error(request, 'Profile not found.')
        return redirect('home')

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.save()

        if profile:
            if hasattr(profile, 'phone_number'):
                profile.phone_number = request.POST.get('profile_phone_number', profile.phone_number)
            if hasattr(profile, 'flat_number'):
                profile.flat_number = request.POST.get('flat_number', profile.flat_number)
            if hasattr(profile, 'building_name'):
                profile.building_name = request.POST.get('building_name', profile.building_name)
            if hasattr(profile, 'shift'):
                profile.shift = request.POST.get('shift', profile.shift)
            if 'profile_photo' in request.FILES:
                profile.profile_photo = request.FILES['profile_photo']
            profile.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:user_profile')

    return render(request, 'edit_profile.html', {'profile': profile})


def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile_number']
            user = (
                CustomUser.objects.filter(phone_number=mobile, user_type__in=['resident', 'security']).first()
                or _find_user_by_profile_phone(mobile)
            )
            if user:
                otp_code = generate_otp()
                PasswordResetOTP.objects.create(user=user, otp=otp_code)
                send_sms(user.phone_number or mobile, f'Your password reset OTP is: {otp_code}. Valid for 10 minutes.')
                messages.success(request, 'OTP sent to your registered mobile number.')
                return redirect('accounts:reset_password_verify', user_id=user.id)
            else:
                messages.error(request, 'No account found with this mobile number.')
    else:
        form = ForgotPasswordForm()

    return render(request, 'forgot_password.html', {'form': form})


def reset_password_verify(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id, user_type__in=['resident', 'security'])

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp']
            new_password = form.cleaned_data['new_password']

            reset_otp = PasswordResetOTP.objects.filter(user=user, otp=otp_code, is_used=False).first()
            if reset_otp and reset_otp.is_valid():
                with transaction.atomic():
                    user.set_password(new_password)
                    user.save()
                    reset_otp.is_used = True
                    reset_otp.save()
                log_activity(user, 'user_update', f'Password reset for {user.username}', request)
                messages.success(request, 'Password reset successful! Please login.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired OTP.')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password_verify.html', {'form': form, 'user': user})


# ─── Helper ────────────────────────────────────────────────────────────────────

def _find_user_by_profile_phone(mobile):
    resident = Resident.objects.filter(phone_number=mobile).first()
    if resident and resident.user:
        return resident.user
    guard = SecurityGuard.objects.filter(phone_number=mobile).first()
    if guard and guard.user:
        return guard.user
    return None
