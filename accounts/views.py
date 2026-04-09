from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib import messages
from datetime import timedelta
from .models import CustomUser, Resident, SecurityGuard, Admin, PasswordResetOTP
from .forms import ResidentRegistrationForm, SecurityGuardRegistrationForm, generate_employee_id, ForgotPasswordForm, ResetPasswordForm
from core.utils import log_activity, generate_otp, send_sms
from audit.models import SystemAudit


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('dashboard:admin_dashboard')
        elif request.user.user_type == 'resident':
            return redirect('visitors:visitor_dashboard')
        elif request.user.user_type == 'security':
            return redirect('visitors:visitor_dashboard')
    return render(request, 'home.html')


def user_login(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Log login activity
            log_activity(user, 'user_login', f'User {user.username} logged in', request)
            
            # Redirect based on user type
            if user.user_type == 'admin':
                return redirect('dashboard:admin_dashboard')
            elif user.user_type == 'resident':
                return redirect('visitors:visitor_dashboard')
            elif user.user_type == 'security':
                return redirect('visitors:visitor_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')


def user_logout(request):
    """User logout view"""
    if request.user.is_authenticated:
        log_activity(request.user, 'user_logout', f'User {request.user.username} logged out', request)
        logout(request)
    
    return redirect('home')


def register_resident(request):
    """Register a new resident"""
    if request.method == 'POST':
        form = ResidentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create user
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type='resident',
                phone_number=form.cleaned_data['phone_number']  # Save phone number to CustomUser
            )
            
            # Create resident profile
            resident = Resident.objects.create(
                user=user,
                flat_number=form.cleaned_data['flat_number'],
                phone_number=form.cleaned_data['phone_number'],
                building_name=form.cleaned_data.get('building_name', 'Building A'),
                profile_photo=form.cleaned_data.get('profile_photo')
            )
            
            # Log activity
            log_activity(user, 'user_create', f'Resident {user.username} registered', request)
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('accounts:login')
    else:
        form = ResidentRegistrationForm()
    
    return render(request, 'register_resident.html', {'form': form})


def register_security_guard_simple(request):
    """Simple test view for guard registration"""
    if request.method == 'POST':
        print("DEBUG: SIMPLE Guard registration POST request received")
        form = SecurityGuardRegistrationForm(request.POST, request.FILES)
        print(f"DEBUG: SIMPLE Form data keys: {list(request.POST.keys())}")
        print(f"DEBUG: SIMPLE Files data keys: {list(request.FILES.keys())}")
        
        if form.is_valid():
            print("DEBUG: SIMPLE Form is valid")
            print(f"DEBUG: SIMPLE Cleaned data: {form.cleaned_data}")
            
            # Check if photo is in cleaned data
            photo = form.cleaned_data.get('profile_photo')
            print(f"DEBUG: SIMPLE Photo in cleaned_data: {photo}")
            if photo:
                print(f"DEBUG: SIMPLE Photo name: {photo.name}")
                print(f"DEBUG: SIMPLE Photo size: {photo.size} bytes")
                print(f"DEBUG: SIMPLE Photo content type: {photo.content_type}")
            
            # Create user
            print("DEBUG: SIMPLE Creating CustomUser...")
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type='security',
                phone_number=form.cleaned_data['phone_number']
            )
            print(f"DEBUG: SIMPLE User created: {user.username} (ID: {user.id})")
            
            # Create security guard profile with photo
            print("DEBUG: SIMPLE Creating SecurityGuard profile...")
            for attempt in range(1, 6):
                try:
                    employee_id = generate_employee_id()
                    print(f"DEBUG: SIMPLE Attempt {attempt}: Generated employee_id: {employee_id}")
                    
                    guard_data = {
                        'user': user,
                        'employee_id': employee_id,
                        'phone_number': form.cleaned_data['phone_number'],
                        'shift': form.cleaned_data.get('shift', 'morning'),
                    }
                    
                    if photo:
                        guard_data['profile_photo'] = photo
                        print("DEBUG: SIMPLE Adding photo to guard creation data")
                    
                    print(f"DEBUG: SIMPLE Guard creation data: {guard_data}")
                    
                    guard = SecurityGuard.objects.create(**guard_data)
                    print(f"DEBUG: SIMPLE SecurityGuard created: {guard.user.get_full_name()} (ID: {guard.id})")
                    
                    if guard.profile_photo:
                        print(f"DEBUG: SIMPLE Guard photo saved: {guard.profile_photo.name}")
                        print(f"DEBUG: SIMPLE Guard photo path: {guard.profile_photo.path}")
                    else:
                        print("DEBUG: SIMPLE No guard photo saved")
                    
                    break
                except Exception as e:
                    print(f"DEBUG: SIMPLE Attempt {attempt} failed: {e}")
                    if attempt == 5:
                        messages.error(request, 'Unable to generate unique employee ID. Please try again.')
                        return redirect('accounts:register_guard')
                    continue
            
            messages.success(request, f'Registration successful! Your Employee ID is: {employee_id}. Please login.')
            return redirect('accounts:login')
        else:
            print("DEBUG: SIMPLE Form is invalid")
            print(f"DEBUG: SIMPLE Form errors: {form.errors}")
    else:
        print("DEBUG: SIMPLE Guard registration GET request")
        form = SecurityGuardRegistrationForm()
    
    return render(request, 'register_guard_simple.html', {'form': form})


def register_security_guard(request):
    """Register a new security guard"""
    if request.method == 'POST':
        print("DEBUG: Guard registration POST request received")
        form = SecurityGuardRegistrationForm(request.POST, request.FILES)
        print(f"DEBUG: Form data keys: {list(request.POST.keys())}")
        print(f"DEBUG: Files data keys: {list(request.FILES.keys())}")
        
        if form.is_valid():
            print("DEBUG: Form is valid")
            print(f"DEBUG: Cleaned data: {form.cleaned_data}")
            
            # Check if photo is in cleaned data
            photo = form.cleaned_data.get('profile_photo')
            print(f"DEBUG: Photo in cleaned_data: {photo}")
            if photo:
                print(f"DEBUG: Photo name: {photo.name}")
                print(f"DEBUG: Photo size: {photo.size} bytes")
                print(f"DEBUG: Photo content type: {photo.content_type}")
            
            # Create user
            print("DEBUG: Creating CustomUser...")
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type='security',
                phone_number=form.cleaned_data['phone_number']  # Save phone number to CustomUser
            )
            print(f"DEBUG: User created: {user.username} (ID: {user.id})")
            
            # Create security guard profile with photo
            print("DEBUG: Creating SecurityGuard profile...")
            for attempt in range(1, 6):  # Try up to 5 times
                try:
                    employee_id = generate_employee_id()
                    print(f"DEBUG: Attempt {attempt}: Generated employee_id: {employee_id}")
                    
                    guard_data = {
                        'user': user,
                        'employee_id': employee_id,
                        'phone_number': form.cleaned_data['phone_number'],
                        'shift': form.cleaned_data.get('shift', 'morning'),
                    }
                    
                    # Add photo if provided
                    if photo:
                        guard_data['profile_photo'] = photo
                        print("DEBUG: Adding photo to guard creation data")
                    
                    print(f"DEBUG: Guard creation data: {guard_data}")
                    
                    guard = SecurityGuard.objects.create(**guard_data)
                    print(f"DEBUG: SecurityGuard created: {guard.user.get_full_name()} (ID: {guard.id})")
                    
                    if guard.profile_photo:
                        print(f"DEBUG: Guard photo saved: {guard.profile_photo.name}")
                        print(f"DEBUG: Guard photo path: {guard.profile_photo.path}")
                    else:
                        print("DEBUG: No guard photo saved")
                    
                    break
                except Exception as e:
                    print(f"DEBUG: Attempt {attempt} failed: {e}")
                    if attempt == 5:  # Last attempt
                        print("DEBUG: All attempts failed")
                        messages.error(request, 'Unable to generate unique employee ID. Please try again.')
                        return redirect('accounts:register_guard')
                    continue
            
            # Log activity
            log_activity(user, 'user_create', f'Security Guard {user.username} registered', request)
            
            messages.success(request, f'Registration successful! Your Employee ID is: {employee_id}. Please login.')
            return redirect('accounts:login')
        else:
            print("DEBUG: Form is invalid")
            print(f"DEBUG: Form errors: {form.errors}")
            for field, errors in form.errors.items():
                print(f"DEBUG: {field}: {errors}")
    else:
        print("DEBUG: Guard registration GET request")
        form = SecurityGuardRegistrationForm()
    
    return render(request, 'register_guard.html', {'form': form})


@login_required(login_url='accounts:login')
def user_profile(request):
    """User profile view"""
    try:
        print(f"DEBUG: Profile view for user: {request.user.username} (type: {request.user.user_type})")
        
        if request.user.user_type == 'resident':
            profile = request.user.resident
            print(f"DEBUG: Resident profile found: {profile}")
            if profile.profile_photo:
                print(f"DEBUG: Resident photo: {profile.profile_photo.name}")
        elif request.user.user_type == 'security':
            profile = request.user.securityguard
            print(f"DEBUG: SecurityGuard profile found: {profile}")
            if profile.profile_photo:
                print(f"DEBUG: Guard photo: {profile.profile_photo.name}")
                print(f"DEBUG: Guard photo URL: {profile.profile_photo.url}")
            else:
                print("DEBUG: Guard has no photo")
        elif request.user.user_type == 'admin':
            profile = request.user.admin
            print(f"DEBUG: Admin profile found: {profile}")
        else:
            profile = None
            print("DEBUG: No profile found")
        
        return render(request, 'profile.html', {'profile': profile})
    except Exception as e:
        print(f"DEBUG: Profile error: {e}")  # For debugging
        messages.error(request, 'Profile not found')
        return redirect('home')


@login_required(login_url='accounts:login')
def edit_profile(request):
    """Edit user profile"""
    try:
        if request.user.user_type == 'resident':
            profile = request.user.resident
        elif request.user.user_type == 'security':
            profile = request.user.securityguard
        elif request.user.user_type == 'admin':
            profile = request.user.admin
        else:
            profile = None
        
        if request.method == 'POST':
            # Update user info
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            user.save()
            
            # Update profile-specific info
            if profile and hasattr(profile, 'phone_number'):
                profile.phone_number = request.POST.get('profile_phone_number', profile.phone_number)
                if hasattr(profile, 'flat_number'):
                    profile.flat_number = request.POST.get('flat_number', profile.flat_number)
                if hasattr(profile, 'employee_id'):
                    profile.employee_id = request.POST.get('employee_id', profile.employee_id)
                if hasattr(profile, 'shift'):
                    profile.shift = request.POST.get('shift', profile.shift)
                
                # Handle profile photo upload
                if 'profile_photo' in request.FILES:
                    profile.profile_photo = request.FILES['profile_photo']
                
                profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:user_profile')
        
    except Exception as e:
        messages.error(request, f'Error updating profile: {str(e)}')
        return redirect('accounts:user_profile')
    
    return render(request, 'edit_profile.html', {'profile': profile})


def forgot_password(request):
    """Handle forgot password requests for residents and security guards"""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            mobile_number = form.cleaned_data['mobile_number']
            
            # Search by mobile number
            user = CustomUser.objects.filter(
                phone_number=mobile_number, 
                user_type__in=['resident', 'security']
            ).first()
            
            if not user:
                # Also try searching in Resident and SecurityGuard models
                from accounts.models import Resident, SecurityGuard
                resident = Resident.objects.filter(phone_number=mobile_number).first()
                if resident:
                    user = resident.user
                else:
                    guard = SecurityGuard.objects.filter(phone_number=mobile_number).first()
                    if guard:
                        user = guard.user
            
            if user:
                # Generate OTP
                otp = generate_otp()
                PasswordResetOTP.objects.create(user=user, otp=otp)
                
                # Send OTP via SMS
                send_sms(user.phone_number, f"Your password reset OTP is: {otp}")
                
                messages.success(request, f'OTP sent to {user.phone_number}')
                return redirect('accounts:reset_password_verify', user_id=user.id)
            else:
                messages.error(request, 'No account found with this mobile number.')
    
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'forgot_password.html', {'form': form})


def reset_password_verify(request, user_id):
    """Verify OTP and reset password"""
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid user.')
        return redirect('accounts:forgot_password')
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            new_password = form.cleaned_data['new_password']
            
            # Verify OTP
            reset_otp = PasswordResetOTP.objects.filter(
                user=user, 
                otp=otp,
                is_used=False
            ).first()
            
            if reset_otp and reset_otp.is_valid():
                # Reset password
                user.set_password(new_password)
                user.save()
                
                # Mark OTP as used
                reset_otp.is_used = True
                reset_otp.save()
                
                messages.success(request, 'Password reset successfully. Please login with your new password.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired OTP.')
    
    else:
        form = ResetPasswordForm()
    
    return render(request, 'reset_password.html', {'form': form, 'user_id': user_id})


@login_required(login_url='accounts:login')
def user_profile(request):
    """User profile view"""
    try:
        if request.user.user_type == 'resident':
            profile = request.user.resident
        elif request.user.user_type == 'security':
            profile = request.user.securityguard
        elif request.user.user_type == 'admin':
            profile = request.user.admin
        else:
            profile = None
        
        return render(request, 'profile.html', {'profile': profile})
    except Exception as e:
        print(f"Profile error: {e}")  # For debugging
        messages.error(request, 'Profile not found')
        return redirect('home')


def reset_password_verify(request, user_id):
    """Verify OTP and reset password"""
    user = get_object_or_404(CustomUser, id=user_id, user_type__in=['resident', 'security'])
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            new_password = form.cleaned_data['new_password']
            
            # Verify OTP
            reset_otp = PasswordResetOTP.objects.filter(
                user=user, 
                otp=otp, 
                is_used=False
            ).first()
            
            if reset_otp and reset_otp.is_valid():
                # Reset password
                user.set_password(new_password)
                user.save()
                
                # Mark OTP as used
                reset_otp.is_used = True
                reset_otp.save()
                
                # Log successful password reset
                log_activity(user, 'password_reset_success', 
                           f'Password reset successful for {user.username}', 
                           request)
                
                messages.success(request, 'Password reset successful! Please login with your new password.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired OTP. Please request a new one.')
    else:
        form = ResetPasswordForm()
    
    return render(request, 'reset_password_verify.html', {
        'form': form, 
        'user': user
    })
