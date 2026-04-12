"""
Template-based views for the visitors app.
"""
from datetime import timedelta, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import Resident, SecurityGuard
from core.utils import generate_qr_code, log_activity
from .models import Visitor, OTP, GatePass, VisitorHistory
from .forms import VisitorRegistrationForm, OTPVerificationForm, VisitorHistoryFilterForm
from .services import OTPService


# ─── Visitor Registration ──────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def register_visitor(request):
    """Security guard registers a new visitor."""
    guard = getattr(request.user, 'securityguard', None)
    if not guard:
        messages.error(request, 'Access denied. Security guard access required.')
        return redirect('home')

    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                visitor = form.save(commit=False)
                visitor.entry_time = timezone.now()
                visitor.registered_by = guard
                visitor.save()

                otp_code = OTPService.generate_otp()
                OTP.objects.create(
                    visitor=visitor,
                    otp_code=otp_code,
                    expires_at=timezone.now() + timedelta(minutes=5),
                )
                OTPService.send_otp(visitor.resident.phone_number, otp_code, visitor.resident.user.get_full_name())

                VisitorHistory.objects.create(
                    visitor=visitor,
                    entry_time=visitor.entry_time,
                    purpose=visitor.purpose,
                    status='pending',
                )

            log_activity(guard.user, 'visitor_register', f'Visitor {visitor.visitor_name} registered', request)
            log_activity(guard.user, 'otp_generate', f'OTP generated for {visitor.visitor_name}', request)
            return redirect('visitors:verify_otp', visitor_id=visitor.id)
    else:
        form = VisitorRegistrationForm()

    return render(request, 'register_visitor.html', {'form': form})


# ─── OTP Verification ─────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def verify_otp(request, visitor_id):
    visitor = get_object_or_404(Visitor, id=visitor_id)
    otp = get_object_or_404(OTP, visitor=visitor)

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']

            if not otp.is_valid():
                VisitorHistory.objects.filter(visitor=visitor, status='pending').update(status='rejected')
                GatePass.objects.filter(visitor=visitor, status='pending').update(status='rejected')
                messages.error(request, 'OTP has expired or maximum attempts reached.')
            elif otp.verify_otp(entered_otp):
                with transaction.atomic():
                    gate_pass = GatePass.objects.create(
                        visitor=visitor,
                        valid_till=timezone.now() + timedelta(hours=24),
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
                return redirect('visitors:gate_pass_details', pass_id=gate_pass.id)
            else:
                remaining = max(0, 3 - otp.attempts)
                messages.error(request, f'Invalid OTP. {remaining} attempt(s) remaining.')
    else:
        form = OTPVerificationForm()

    return render(request, 'verify_otp.html', {
        'form': form,
        'visitor': visitor,
        'resident': visitor.resident,
    })


# ─── Gate Pass ────────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def gate_pass_details(request, pass_id):
    gate_pass = get_object_or_404(GatePass, id=pass_id)

    if request.user.user_type == 'resident':
        if not hasattr(request.user, 'resident') or gate_pass.visitor.resident != request.user.resident:
            messages.error(request, 'Access denied.')
            return redirect('home')

    return render(request, 'gate_pass_details.html', {
        'gate_pass': gate_pass,
        'visitor': gate_pass.visitor,
        'resident': gate_pass.visitor.resident,
    })


# ─── Exit Tracking ────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def mark_exit(request, visitor_id):
    guard = getattr(request.user, 'securityguard', None)
    if not guard:
        messages.error(request, 'Access denied. Security guard access required.')
        return redirect('home')

    visitor = get_object_or_404(Visitor, id=visitor_id)

    if visitor.exit_time:
        messages.warning(request, 'Exit already recorded for this visitor.')
        return redirect('visitors:visitor_dashboard')

    now = timezone.now()
    with transaction.atomic():
        visitor.exit_time = now
        visitor.save(update_fields=['exit_time'])
        VisitorHistory.objects.filter(visitor=visitor).update(exit_time=now, status='completed')

    log_activity(guard.user, 'visitor_exit', f'Visitor {visitor.visitor_name} marked exit', request)
    messages.success(request, f'Exit recorded for {visitor.visitor_name}.')
    return redirect('visitors:visitor_dashboard')


# ─── Visitor History ──────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def visitor_history(request):
    if request.user.user_type == 'resident' and hasattr(request.user, 'resident'):
        visitors = Visitor.objects.filter(resident=request.user.resident)
    else:
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        visitors = Visitor.objects.filter(created_at__date__gte=seven_days_ago)

    form = VisitorHistoryFilterForm(request.GET)
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        status_filter = form.cleaned_data.get('status')

        if start_date:
            visitors = visitors.filter(created_at__date__gte=start_date)
        if end_date:
            visitors = visitors.filter(created_at__date__lte=end_date)
        if status_filter:
            visitors = visitors.filter(visitorhistory__status=status_filter)

    visitors = visitors.order_by('-created_at')

    history_records = []
    for visitor in visitors:
        history = VisitorHistory.objects.filter(visitor=visitor).first()
        history_records.append(history or _temp_history(visitor))

    return render(request, 'visitor_history.html', {
        'history': history_records,
        'form': form,
    })


# ─── Visitor List ─────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def visitor_list(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    guard_filter = request.GET.get('guard', '')
    resident_filter = request.GET.get('resident', '')

    visitors = Visitor.objects.all().order_by('-created_at')

    if search:
        visitors = visitors.filter(
            Q(visitor_name__icontains=search)
            | Q(mobile_number__icontains=search)
            | Q(purpose__icontains=search)
            | Q(resident__flat_number__icontains=search)
            | Q(identity_number__icontains=search)
        )
    if status_filter:
        ids = VisitorHistory.objects.filter(status=status_filter).values_list('visitor_id', flat=True)
        visitors = visitors.filter(id__in=ids)
    if date_filter:
        try:
            visitors = visitors.filter(created_at__date=datetime.strptime(date_filter, '%Y-%m-%d').date())
        except ValueError:
            pass
    if guard_filter and guard_filter != 'all':
        try:
            visitors = visitors.filter(registered_by_id=int(guard_filter))
        except ValueError:
            pass
    if resident_filter and resident_filter != 'all':
        try:
            visitors = visitors.filter(resident_id=int(resident_filter))
        except ValueError:
            pass

    visitors = visitors.prefetch_related('visitorhistory')
    visitors_with_history = [
        {'visitor': v, 'history': v.visitorhistory.order_by('-created_at').first()}
        for v in visitors
    ]

    return render(request, 'visitor_list.html', {
        'all_visitors': visitors_with_history,
        'total_visitors': visitors.count(),
        'search_query': search,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'guard_filter': guard_filter,
        'resident_filter': resident_filter,
        'guards': SecurityGuard.objects.all(),
        'residents': Resident.objects.all(),
        'status_choices': VisitorHistory.STATUS_CHOICES,
    })


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def dashboard(request):
    today = timezone.now().date()

    if request.user.user_type == 'resident' and hasattr(request.user, 'resident'):
        resident = request.user.resident
        today_visitors = Visitor.objects.filter(resident=resident, entry_time__date=today)
        pending_count = Visitor.objects.filter(resident=resident, visitorhistory__status='pending').count()

        visitors_data = _visitors_with_status(today_visitors)
        return render(request, 'resident_dashboard.html', {
            'resident': resident,
            'today_visitors': today_visitors.count(),
            'pending_count': pending_count,
            'recent_visitors': visitors_data[:10],
            'all_visitors': visitors_data,
        })

    if request.user.user_type in ('security', 'guard') and hasattr(request.user, 'securityguard'):
        guard = request.user.securityguard
        today_visitors = Visitor.objects.filter(registered_by=guard, entry_time__date=today)
        pending_count = Visitor.objects.filter(registered_by=guard, visitorhistory__status='pending').count()

        visitors_data = _visitors_with_status(today_visitors)
        return render(request, 'guard_dashboard_enhanced.html', {
            'security_guard': guard,
            'today_visitors': visitors_data,
            'today_count': today_visitors.count(),
            'pending_count': pending_count,
            'recent_visitors': visitors_data,
        })

    # Admin fallback
    today_visitors = Visitor.objects.filter(entry_time__date=today)
    return render(request, 'admin_dashboard_enhanced.html', {
        'today_visitors': today_visitors.count(),
        'pending_visitors': VisitorHistory.objects.filter(status='pending').count(),
        'recent_visitors': today_visitors.order_by('-entry_time')[:10],
    })


# ─── Visitor Detail ───────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def visitor_detail(request, visitor_id):
    visitor = get_object_or_404(Visitor, id=visitor_id)
    history = VisitorHistory.objects.filter(visitor=visitor).first()
    return render(request, 'visitor_detail.html', {
        'visitor': visitor,
        'visitor_history': history,
    })


# ─── Resident Search (AJAX / JSON) ────────────────────────────────────────────

@login_required(login_url='accounts:login')
def search_residents(request):
    query = request.GET.get('q', '').strip()

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

    data = [
        {
            'id': r.id,
            'name': r.user.get_full_name() if r.user else '',
            'unit': r.flat_number,
            'building': r.building_name or 'N/A',
            'display_name': f"{r.building_name or 'N/A'} - {r.flat_number}",
            'full_display': f"{r.building_name or 'N/A'} - {r.flat_number} - {r.user.get_full_name() if r.user else ''}",
            'phone': r.phone_number,
            'total_visitors': r.visitor_count,
        }
        for r in residents
    ]
    return JsonResponse({'residents': data})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _visitors_with_status(queryset):
    result = []
    for visitor in queryset:
        history = VisitorHistory.objects.filter(visitor=visitor).first()
        if not history or history.status == 'pending':
            computed_status = 'rejected'
        elif history.status == 'in_process':
            computed_status = 'approved'
        elif visitor.exit_time:
            computed_status = 'completed'
        else:
            computed_status = 'rejected'
        result.append({'visitor': visitor, 'history': history, 'status': computed_status})
    return result


class _TempHistory:
    """Stand-in when a VisitorHistory record doesn't exist yet."""
    def __init__(self, visitor):
        self.visitor = visitor
        self.purpose = visitor.purpose
        self.entry_time = visitor.entry_time
        self.exit_time = visitor.exit_time
        self.status = 'approved'

    def get_duration_display(self):
        if self.exit_time and self.entry_time:
            total = (self.exit_time - self.entry_time).total_seconds()
            h, m = int(total // 3600), int((total % 3600) // 60)
            if h:
                return f'{h}h {m}m'
            return f'{m}m' if m else 'Less than 1m'
        return 'N/A'


def _temp_history(visitor):
    return _TempHistory(visitor)
