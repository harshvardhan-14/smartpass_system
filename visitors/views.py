from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Visitor, OTP, GatePass, VisitorHistory
from .forms import VisitorRegistrationForm, OTPVerificationForm, ResidentApprovalForm, VisitorHistoryFilterForm
from .services import OTPService
from core.utils import generate_qr_code, log_activity
from accounts.models import CustomUser, Resident, SecurityGuard
import qrcode
from io import BytesIO
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json


def update_expired_otps():
    """Update expired OTPs to rejected status"""
    current_time = timezone.now()
    expired_otps = OTP.objects.filter(
        expires_at__lt=current_time,
        is_verified=False
    )
    
    updated_count = 0
    for otp in expired_otps:
        try:
            history = VisitorHistory.objects.get(visitor=otp.visitor)
            if history.status == 'pending':
                history.status = 'rejected'
                history.save()
                updated_count += 1
                
                # Also update gate pass status if exists
                gate_pass = GatePass.objects.filter(visitor=otp.visitor).first()
                if gate_pass and gate_pass.status == 'pending':
                    gate_pass.status = 'rejected'
                    gate_pass.save()
        except VisitorHistory.DoesNotExist:
            pass
    
    return updated_count


@login_required(login_url='accounts:login')
def register_visitor(request):
    """Register a new visitor - PROJECT REQUIREMENTS COMPLIANT"""
    try:
        security_guard = request.user.securityguard
    except SecurityGuard.DoesNotExist:
        messages.error(request, 'Access denied. Security guard access required.')
        return redirect('home')
    
    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create visitor with all required fields
            visitor = form.save(commit=False)
            visitor.entry_time = timezone.now()
            visitor.registered_by = security_guard
            visitor.save()
            
            # Generate OTP
            otp_code = OTPService.generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            
            # Create OTP record
            otp = OTP.objects.create(
                visitor=visitor,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            # Send OTP to resident
            OTPService.send_otp(visitor.resident.phone_number, otp_code, visitor.resident.user.get_full_name())
            
            # Log activities
            log_activity(security_guard.user, 'visitor_register', f'Visitor {visitor.visitor_name} registered', request)
            log_activity(security_guard.user, 'otp_generate', f'OTP generated for {visitor.visitor_name}', request)
            
            # Create visitor history record
            VisitorHistory.objects.create(
                visitor=visitor,
                entry_time=visitor.entry_time,
                purpose=visitor.purpose,
                status='pending'
            )
            
            return redirect('visitors:verify_otp', visitor_id=visitor.id)
    else:
        form = VisitorRegistrationForm()
    
    return render(request, 'register_visitor.html', {'form': form})


@login_required(login_url='accounts:login')
def verify_otp(request, visitor_id):
    """Verify OTP for visitor"""
    visitor = get_object_or_404(Visitor, id=visitor_id)
    otp = get_object_or_404(OTP, visitor=visitor)
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            
            if otp.verify_otp(entered_otp):
                # OTP verified - create gate pass
                valid_till = timezone.now() + timedelta(hours=24)
                gate_pass = GatePass.objects.create(
                    visitor=visitor,
                    valid_till=valid_till,
                    status='approved'
                )
                
                # Generate QR code
                qr_data = f"Gate Pass ID: {gate_pass.pass_id}\nVisitor: {visitor.visitor_name}\nResident: {visitor.resident.user.get_full_name()}\nFlat: {visitor.resident.flat_number}"
                gate_pass.qr_code = generate_qr_code(qr_data)
                gate_pass.save()
                
                # Update visitor history
                history = VisitorHistory.objects.get(visitor=visitor)
                history.status = 'in_process'  # Set to 'In Process' after OTP verification
                history.save()
                
                # Log activities
                log_activity(request.user, 'otp_verify', f'OTP verified for {visitor.visitor_name}', request)
                log_activity(request.user, 'gate_pass_issue', f'Gate pass issued: {gate_pass.pass_id}', request)
                
                return redirect('visitors:gate_pass_details', pass_id=gate_pass.id)
            else:
                # Check if OTP is now invalid (expired or attempts exceeded)
                if not otp.is_valid():
                    messages.error(request, 'OTP has expired or maximum attempts reached.')
                    # Update visitor history to rejected
                    try:
                        history = VisitorHistory.objects.get(visitor=visitor)
                        history.status = 'rejected'
                        history.save()
                        
                        # Also update gate pass status
                        gate_pass = GatePass.objects.filter(visitor=visitor).first()
                        if gate_pass and gate_pass.status == 'pending':
                            gate_pass.status = 'rejected'
                            gate_pass.save()
                    except VisitorHistory.DoesNotExist:
                        pass
                else:
                    messages.error(request, 'Invalid OTP. Please try again.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'verify_otp.html', {
        'form': form,
        'visitor': visitor,
        'resident': visitor.resident
    })


@login_required(login_url='accounts:login')
def gate_pass_details(request, pass_id):
    """Show gate pass details"""
    gate_pass = get_object_or_404(GatePass, id=pass_id)
    
    # Check if user has permission to view this gate pass
    if hasattr(request.user, 'securityguard'):
        # Security guard can view all gate passes
        pass
    elif hasattr(request.user, 'resident'):
        # Resident can only view gate passes for their visitors
        if gate_pass.visitor.resident != request.user.resident:
            messages.error(request, 'Access denied.')
            return redirect('home')
    else:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return render(request, 'gate_pass_details.html', {
        'gate_pass': gate_pass,
        'visitor': gate_pass.visitor,
        'resident': gate_pass.visitor.resident
    })


@login_required(login_url='accounts:login')
def visitor_history(request):
    """View visitor history"""
    from datetime import timedelta
    seven_days_ago = timezone.now().date() - timedelta(days=7)
    
    # Check user role and filter accordingly
    if hasattr(request.user, 'resident'):
        # Resident can only see their visitors
        visitors = Visitor.objects.filter(resident=request.user.resident)
    elif hasattr(request.user, 'securityguard'):
        # Security guard can see all visitors
        visitors = Visitor.objects.filter(created_at__date__gte=seven_days_ago)
    else:
        # Admin can see all visitors
        visitors = Visitor.objects.filter(created_at__date__gte=seven_days_ago)
    
    # Apply filters
    form = VisitorHistoryFilterForm(request.GET)
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        status = form.cleaned_data.get('status')
        
        print(f"DEBUG: Form valid - Start: {start_date}, End: {end_date}, Status: {status}")
        print(f"DEBUG: Visitors before filtering: {visitors.count()}")
        
        if start_date:
            visitors = visitors.filter(created_at__date__gte=start_date)
            print(f"DEBUG: After start_date filter: {visitors.count()}")
        if end_date:
            # Include the entire end_date (until 23:59:59)
            from datetime import time
            end_datetime = datetime.combine(end_date, time(23, 59, 59))
            visitors = visitors.filter(created_at__lte=end_datetime)
            print(f"DEBUG: After end_date filter: {visitors.count()}")
        if status:
            visitors = visitors.filter(visitorhistory__status=status)
            print(f"DEBUG: After status filter: {visitors.count()}")
    
    print(f"DEBUG: Final visitor count: {visitors.count()}")
    
    visitors = visitors.order_by('-created_at')
    
    # Get visitor history records for template
    history_records = []
    for visitor in visitors:
        history = VisitorHistory.objects.filter(visitor=visitor).first()
        if history:
            history_records.append(history)
        else:
            # Create a temporary object for template compatibility
            class TempHistory:
                def __init__(self, visitor):
                    self.visitor = visitor
                    self.purpose = visitor.purpose
                    self.entry_time = visitor.entry_time
                    self.exit_time = visitor.exit_time
                    self.status = 'approved'
                
                def get_duration_display(self):
                    if self.exit_time and self.entry_time:
                        duration = self.exit_time - self.entry_time
                        total_seconds = duration.total_seconds()
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        
                        if hours > 0:
                            return f"{hours}h {minutes}m"
                        elif minutes > 0:
                            return f"{minutes}m"
                        else:
                            return "Less than 1m"
                    return "N/A"
            
            history_records.append(TempHistory(visitor))
    
    print(f"DEBUG: History records created: {len(history_records)}")
    for i, record in enumerate(history_records):
        print(f"DEBUG: Record {i+1}: {record.visitor.visitor_name} - {record.status}")
    
    return render(request, 'visitor_history.html', {
        'history': history_records,
        'visitors': visitors,  # Keep for backward compatibility
        'form': form
    })


@login_required(login_url='accounts:login')
def mark_exit(request, visitor_id):
    """Mark visitor exit"""
    try:
        security_guard = request.user.securityguard
    except SecurityGuard.DoesNotExist:
        messages.error(request, 'Access denied. Security guard access required.')
        return redirect('home')
    
    visitor = get_object_or_404(Visitor, id=visitor_id)
    
    # Update visitor history
    try:
        history = VisitorHistory.objects.get(visitor=visitor)
        history.exit_time = timezone.now()
        history.status = 'completed'
        history.save()
        
        # Update visitor model exit time
        visitor.exit_time = timezone.now()
        visitor.save()
        
        log_activity(security_guard.user, 'visitor_exit', f'Visitor {visitor.visitor_name} marked exit', request)
        messages.success(request, f'Exit marked for {visitor.visitor_name}')
    except VisitorHistory.DoesNotExist:
        messages.error(request, 'Visitor history not found.')
    
    return redirect('visitors:visitor_dashboard')


@login_required(login_url='accounts:login')
def visitor_list(request):
    """View all visitors list with comprehensive filtering"""
    # Update expired OTPs only once per session
    if not request.session.get('expired_otps_checked', False):
        update_expired_otps()
        request.session['expired_otps_checked'] = True
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    guard_filter = request.GET.get('guard', '')
    resident_filter = request.GET.get('resident', '')
    
    # Base visitor query based on user role
    if hasattr(request.user, 'securityguard'):
        # Security guard sees all visitors (so they can see who's in the building)
        visitors = Visitor.objects.all().order_by('-created_at')
    else:
        # Admin or other roles see all visitors
        visitors = Visitor.objects.all().order_by('-created_at')
    
    # Apply search filter - searches across multiple fields
    if search_query:
        visitors = visitors.filter(
            Q(visitor_name__icontains=search_query) |
            Q(mobile_number__icontains=search_query) |
            Q(purpose__icontains=search_query) |
            Q(resident__user__first_name__icontains=search_query) |
            Q(resident__user__last_name__icontains=search_query) |
            Q(resident__flat_number__icontains=search_query) |
            Q(identity_number__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        # Get visitor IDs with the specified status
        visitor_ids_with_status = VisitorHistory.objects.filter(
            status=status_filter
        ).values_list('visitor_id', flat=True).distinct()
        
        visitors = visitors.filter(id__in=visitor_ids_with_status)
    
    # Apply date filter
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            # Filter by created_at (registration date) since entry_time might be null
            visitors = visitors.filter(created_at__date=filter_date)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Apply guard filter
    if guard_filter and guard_filter != 'all':
        try:
            guard_id = int(guard_filter)
            visitors = visitors.filter(registered_by_id=guard_id)
        except ValueError:
            pass  # Invalid guard ID, ignore filter
    
    # Apply resident filter
    if resident_filter and resident_filter != 'all':
        try:
            resident_id = int(resident_filter)
            visitors = visitors.filter(resident_id=resident_id)
        except ValueError:
            pass  # Invalid resident ID, ignore filter
    
    # Get visitors with their history optimized
    visitors = visitors.prefetch_related('visitorhistory')
    
    visitors_with_history = []
    for visitor in visitors:
        # Get the latest visitor history record
        history_records = visitor.visitorhistory.all().order_by('-created_at')
        history = history_records.first() if history_records else None
        
        visitor_data = {
            'visitor': visitor,
            'history': history
        }
        visitors_with_history.append(visitor_data)
    
    # Get filter options for dropdowns
    guards = SecurityGuard.objects.all()
    residents = Resident.objects.all()
    status_choices = VisitorHistory.STATUS_CHOICES
    
    context = {
        'all_visitors': visitors_with_history,
        'total_visitors': visitors.count(),
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'guard_filter': guard_filter,
        'resident_filter': resident_filter,
        'guards': guards,
        'residents': residents,
        'status_choices': status_choices,
        'filter_description': _get_filter_description(search_query, status_filter, date_filter, guard_filter, resident_filter),
    }
    return render(request, 'visitor_list.html', context)


def _get_filter_description(search, status, date, guard, resident):
    """Generate human-readable filter description"""
    descriptions = []
    
    if search:
        descriptions.append(f"Search: '{search}'")
    
    if status:
        status_display = dict(VisitorHistory.STATUS_CHOICES).get(status, status.title())
        descriptions.append(f"Status: {status_display}")
    
    if date and date != 'all':
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').strftime('%B %d, %Y')
            descriptions.append(f"Date: {parsed_date}")
        except Exception as e:
            print(f"Date parsing error: {e}")
            descriptions.append(f"Date: {date}")
    
    if guard and guard != 'all':
        try:
            guard_obj = SecurityGuard.objects.get(id=int(guard))
            descriptions.append(f"Guard: {guard_obj.user.get_full_name()}")
        except SecurityGuard.DoesNotExist:
            descriptions.append(f"Guard: Unknown")
    
    if resident and resident != 'all':
        try:
            resident_obj = Resident.objects.get(id=int(resident))
            descriptions.append(f"Resident: {resident_obj.user.get_full_name()}")
        except Resident.DoesNotExist:
            descriptions.append(f"Resident: Unknown")
    
    return " | ".join(descriptions) if descriptions else "All Visitors"


@login_required(login_url='accounts:login')
def dashboard(request):
    """Visitor management dashboard"""
    # Check and update expired OTPs (only once per session)
    if not request.session.get('expired_otps_checked', False):
        updated_count = update_expired_otps()
        if updated_count > 0:
            messages.info(request, f'Updated {updated_count} expired OTPs to rejected status.')
        request.session['expired_otps_checked'] = True
    
    # Get statistics based on user role
    from datetime import timedelta
    seven_days_ago = timezone.now().date() - timedelta(days=7)
    
    if hasattr(request.user, 'resident'):
        # Resident dashboard
        today_visitors = Visitor.objects.filter(
            resident=request.user.resident,
            entry_time__date=timezone.now().date()
        )
        pending_visitors = Visitor.objects.filter(
            resident=request.user.resident,
            visitorhistory__status='pending'
        )
        template_name = 'resident_dashboard.html'
        
        # Get visitors with their history using direct query to avoid relationship issues
        today_visitors_with_history = []
        for visitor in today_visitors:
            history = VisitorHistory.objects.filter(visitor=visitor).first()
            # Determine status based on OTP verification
            if not history or history.status == 'pending':
                status = 'rejected'  # OTP not verified
            elif history.status == 'in_process':
                status = 'approved'  # Visitor is in premises
            elif visitor.exit_time:
                status = 'completed'  # Visitor has left
            else:
                status = 'rejected'  # Default to rejected for safety
            
            visitor_data = {
                'visitor': visitor,
                'history': history,
                'status': status  # Add computed status
            }
            today_visitors_with_history.append(visitor_data)
        
        context = {
            'resident': request.user.resident,  # Add resident object to context
            'today_visitors': today_visitors.count(),
            'pending_count': pending_visitors.count(),  # Fix variable name
            'recent_visitors': today_visitors_with_history[:10],  # Use the correct data structure
            'all_visitors': today_visitors_with_history
        }
        return render(request, template_name, context)
    elif hasattr(request.user, 'securityguard'):
        # Security guard dashboard
        security_guard = request.user.securityguard
        
        # Update expired OTPs every time guard visits dashboard
        update_expired_otps()
        
        # Show visitors either registered by this guard OR marked exit by this guard
        today = timezone.now().date()
        
        # Get visitors registered by this guard
        registered_visitors = Visitor.objects.filter(
            entry_time__date=today,
            registered_by=security_guard
        )
        
        # Get visitors marked exit by this guard (from audit logs)
        from audit.models import SystemAudit
        exit_visitor_ids = SystemAudit.objects.filter(
            user=request.user,
            action_type='visitor_exit',
            timestamp__date=today
        ).values_list('description', flat=True)
        
        # Extract visitor names from exit descriptions
        exit_visitor_names = []
        for desc in exit_visitor_ids:
            # Extract visitor name from "Visitor [name] marked exit"
            if " marked exit" in desc:
                visitor_name = desc.replace("Visitor ", "").replace(" marked exit", "")
                exit_visitor_names.append(visitor_name)
        
        # Get visitors who were marked exit by this guard
        exit_visitors = Visitor.objects.filter(
            entry_time__date=today,
            visitor_name__in=exit_visitor_names
        )
        
        # Combine both sets (avoid duplicates)
        today_visitors = registered_visitors.union(exit_visitors)
        
        # For pending visitors, also filter by this guard's visitors
        pending_visitors = Visitor.objects.filter(
            visitorhistory__status='pending',
            registered_by=security_guard
        )
        
        template_name = 'guard_dashboard_enhanced.html'
        
        # Get visitors with their history using direct query to avoid relationship issues
        today_visitors_with_history = []
        for visitor in today_visitors:
            history = VisitorHistory.objects.filter(visitor=visitor).first()
            # Determine status based on OTP verification
            if not history or history.status == 'pending':
                status = 'rejected'  # OTP not verified
            elif history.status == 'in_process':
                status = 'approved'  # Visitor is in premises
            elif visitor.exit_time:
                status = 'completed'  # Visitor has left
            else:
                status = 'rejected'  # Default to rejected for safety
            
            visitor_data = {
                'visitor': visitor,
                'history': history,
                'status': status  # Add computed status
            }
            today_visitors_with_history.append(visitor_data)
        
        context = {
            'security_guard': security_guard,
            'today_visitors': today_visitors_with_history,
            'today_count': today_visitors.count(),
            'pending_count': pending_visitors.count(),
            'recent_visitors': today_visitors_with_history
        }
        return render(request, template_name, context)
    else:
        # Admin dashboard - fallback
        today_visitors = Visitor.objects.filter(
            entry_time__date=timezone.now().date()
        )
        pending_visitors = Visitor.objects.filter(
            visitorhistory__status='pending'
        )
        template_name = 'admin_dashboard_enhanced.html'  # Fallback
        context = {
            'today_visitors': today_visitors.count(),
            'pending_visitors': pending_visitors.count(),
            'recent_visitors': today_visitors.order_by('-entry_time')[:10]
        }
        return render(request, template_name, context)


@login_required(login_url='accounts:login')
def visitor_detail(request, visitor_id):
    """View detailed information about a specific visitor"""
    try:
        visitor = get_object_or_404(Visitor, id=visitor_id)
        
        # Get visitor history if available
        visitor_history = VisitorHistory.objects.filter(visitor=visitor).first()
        
        context = {
            'visitor': visitor,
            'visitor_history': visitor_history,
            'page_title': f'Visitor Details - {visitor.visitor_name}'
        }
        
        return render(request, 'visitor_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error retrieving visitor details: {str(e)}')
        return redirect('visitors:visitor_history')


@login_required(login_url='accounts:login')
def search_residents(request):
    """API endpoint to search residents dynamically"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        # Allow empty query to show all residents (for popular residents feature)
        try:
            # Get all residents matching building/flat search
            if query:
                residents = Resident.objects.filter(
                    Q(flat_number__icontains=query) |
                    Q(building_name__icontains=query)
                ).select_related('user')
            else:
                # Get all residents for popular residents display
                residents = Resident.objects.all().select_related('user')
            
            # Annotate with visitor count to prioritize frequently visited residents
            from django.db.models import Count, Case, When, IntegerField
            residents = residents.annotate(
                visitor_count=Count('visitors'),
                has_recent_visitors=Count(
                    Case(
                        When(visitors__created_at__gte=timezone.now() - timedelta(days=30), then=1),
                        output_field=IntegerField(),
                    )
                )
            ).order_by('-has_recent_visitors', '-visitor_count', 'building_name', 'flat_number')[:20]
            
            residents_data = []
            for resident in residents:
                # Check if this resident has recent visitors (last 30 days)
                recent_visitors = Visitor.objects.filter(
                    resident=resident,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count()
                
                # Get total visitor count
                total_visitors = Visitor.objects.filter(resident=resident).count()
                
                residents_data.append({
                    'id': resident.id,
                    'name': f"{resident.user.first_name} {resident.user.last_name}".strip(),
                    'email': resident.user.email,
                    'phone': resident.phone_number,
                    'unit': resident.flat_number,
                    'building': resident.building_name or 'N/A',
                    'display_name': f"{resident.building_name or 'N/A'} - {resident.flat_number}",
                    'full_display': f"{resident.building_name or 'N/A'} - {resident.flat_number} - {resident.user.first_name} {resident.user.last_name}".strip(),
                    'recent_visitors': recent_visitors,
                    'total_visitors': total_visitors,
                    'is_frequent': total_visitors > 5,  # Mark as frequent if more than 5 visitors
                    'has_recent': recent_visitors > 0  # Has recent visitors
                })
            
            return JsonResponse({'residents': residents_data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
