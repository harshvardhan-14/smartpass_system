from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
import csv
from datetime import datetime, timedelta

# Import models
from accounts.models import CustomUser, Resident, SecurityGuard, Admin
from accounts.decorators import admin_required
from visitors.models import Visitor, GatePass, VisitorHistory
from audit.models import SystemAudit
from audit.services import AuditService
from .models import DashboardSettings


@admin_required
def admin_dashboard(request):
    """Admin dashboard view with comprehensive filtering"""
    # Try to get admin user, but don't redirect if it doesn't exist
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        # Create admin user if it doesn't exist
        admin_user = Admin.objects.create(user=request.user)
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    action_filter = request.GET.get('action_type', 'all')
    status_filter = request.GET.get('status', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Get statistics
    total_users = CustomUser.objects.count()
    total_residents = Resident.objects.count()
    total_guards = SecurityGuard.objects.count()
    today_visitors = Visitor.objects.filter(
        entry_time__date=timezone.now().date()
    ).count()
    
    # Get recent admin activities with filtering
    recent_activities = SystemAudit.objects.all()
    
    # Apply search filter
    if search_query:
        recent_activities = recent_activities.filter(
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )
    
    # Apply action type filter
    if action_filter != 'all':
        recent_activities = recent_activities.filter(action_type=action_filter)
    
    # Apply status filter
    if status_filter != 'all':
        recent_activities = recent_activities.filter(status=status_filter)
    
    # Apply date range filter
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            recent_activities = recent_activities.filter(timestamp__gte=start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            recent_activities = recent_activities.filter(timestamp__lte=end_datetime)
        except ValueError:
            pass
    
    activities_qs = recent_activities.order_by('-timestamp')
    activity_per_page = 10
    activity_paginator = Paginator(activities_qs, activity_per_page)
    activity_page_num = request.GET.get('page', 1)
    try:
        activity_page_num = int(activity_page_num)
    except (TypeError, ValueError):
        activity_page_num = 1
    try:
        activities_page = activity_paginator.page(activity_page_num)
    except PageNotAnInteger:
        activities_page = activity_paginator.page(1)
    except EmptyPage:
        activities_page = activity_paginator.page(activity_paginator.num_pages)

    recent_activities = activities_page

    # Get filter options
    action_types = SystemAudit.ACTION_TYPES
    status_types = SystemAudit.STATUS_TYPES

    # Generate filter description
    filter_description = _get_admin_filter_description(search_query, action_filter, status_filter, start_date, end_date)

    act_nav_params = request.GET.copy()
    act_nav_params.pop('page', None)
    activities_filter_query = act_nav_params.urlencode()

    # Sidebar: compact recent slice (unchanged count for stats strip)
    recent_system_activities = SystemAudit.objects.order_by('-timestamp')[:10]
    
    # Get visitor statistics
    visitor_stats = {
        'total': Visitor.objects.count(),
        'today': today_visitors,
        'this_week': Visitor.objects.filter(
            entry_time__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'active': Visitor.objects.filter(exit_time__isnull=True).count(),
    }
    
    # Get gate pass statistics
    gate_pass_stats = {
        'total': GatePass.objects.count(),
        'active': GatePass.objects.filter(status='approved').count(),
        'expired': GatePass.objects.filter(status='rejected').count(),
        'today': GatePass.objects.filter(
            issue_time__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'admin_user': admin_user,
        'total_users': total_users,
        'total_residents': total_residents,
        'total_guards': total_guards,
        'today_visitors': today_visitors,
        'recent_activities': recent_activities,
        'activities_page': activities_page,
        'recent_system_activities': recent_system_activities,
        'visitor_stats': visitor_stats,
        'gate_pass_stats': gate_pass_stats,
        'action_types': action_types,
        'status_types': status_types,
        'search_query': search_query,
        'action_filter': action_filter,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
        'filter_description': filter_description,
        'activities_filter_query': activities_filter_query,
    }

    return render(request, 'admin_dashboard_enhanced.html', context)


@login_required(login_url='accounts:login')
def user_groups(request):
    """View all users and their group assignments with comprehensive filtering"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    user_type_filter = request.GET.get('user_type', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'username')
    def _safe_page(val, default=1):
        try:
            p = int(val)
            return p if p >= 1 else default
        except (TypeError, ValueError):
            return default

    page_admin = _safe_page(request.GET.get('page_admin'))
    page_resident = _safe_page(request.GET.get('page_resident'))
    page_security = _safe_page(request.GET.get('page_security'))

    filter_params = request.GET.copy()
    for _pk in ('page_admin', 'page_resident', 'page_security', 'page'):
        filter_params.pop(_pk, None)
    filter_query = filter_params.urlencode()

    per_page = 8
    
    # Get all users with filtering
    users = CustomUser.objects.all()
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply user type filter
    if user_type_filter:
        if user_type_filter == 'security':
            users = users.filter(user_type__in=['guard', 'security'])
        else:
            users = users.filter(user_type=user_type_filter)
    
    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Apply sorting
    if sort_by == 'name':
        users = users.order_by('first_name', 'last_name')
    elif sort_by == 'date_joined':
        users = users.order_by('-date_joined')
    elif sort_by == 'last_login':
        users = users.order_by('-last_login')
    else:  # username
        users = users.order_by('username')
    
    # Group users by type with proper profile checking
    user_groups = {}
    
    # Apply sorting to filtered users
    if sort_by == 'name':
        users = users.order_by('first_name', 'last_name')
    elif sort_by == 'date_joined':
        users = users.order_by('-date_joined')
    elif sort_by == 'last_login':
        users = users.order_by('-last_login')
    else:
        users = users.order_by('username')
    
    # Now group filtered users by type with proper status checking
    if user_type_filter == 'admin' or not user_type_filter:
        admins = users.filter(user_type='admin')
        # Check profile existence for proper status
        admin_users_with_status = []
        for admin in admins:
            try:
                admin_profile = Admin.objects.get(user=admin)
                # Profile exists, check user active status
                is_active_status = admin.is_active and not admin_profile.is_deleted if hasattr(admin_profile, 'is_deleted') else admin.is_active
                admin_users_with_status.append({
                    'user': admin,
                    'is_active': is_active_status,
                    'profile_deleted': False
                })
            except Admin.DoesNotExist:
                # Profile doesn't exist
                admin_users_with_status.append({
                    'user': admin,
                    'is_active': False,  # No profile means inactive
                    'profile_deleted': True
                })
        
        # Apply status filter to admin users
        if status_filter == 'active':
            admin_users_with_status = [user for user in admin_users_with_status if user['is_active']]
        elif status_filter == 'inactive':
            admin_users_with_status = [user for user in admin_users_with_status if not user['is_active']]
        
        if admin_users_with_status:
            admin_paginator = Paginator(admin_users_with_status, per_page)
            try:
                admin_page_obj = admin_paginator.page(page_admin)
            except PageNotAnInteger:
                admin_page_obj = admin_paginator.page(1)
            except EmptyPage:
                admin_page_obj = admin_paginator.page(admin_paginator.num_pages)

            user_groups['Administrators'] = admin_page_obj
    
    if user_type_filter == 'resident' or not user_type_filter:
        # Get residents with their user data in one query
        residents = users.filter(user_type='resident').select_related('resident')
        
        resident_users_with_status = []
        for resident in residents:
            try:
                # Use the pre-fetched resident relationship
                resident_profile = resident.resident
                # Profile exists, check user active status
                is_active_status = resident.is_active and not resident_profile.is_deleted if hasattr(resident_profile, 'is_deleted') else resident.is_active
                resident_users_with_status.append({
                    'user': resident,
                    'is_active': is_active_status,
                    'profile_deleted': False
                })
            except Resident.DoesNotExist:
                # Profile doesn't exist
                resident_users_with_status.append({
                    'user': resident,
                    'is_active': False,  # No profile means inactive
                    'profile_deleted': True
                })
        
        # Apply status filter to resident users
        if status_filter == 'active':
            resident_users_with_status = [user for user in resident_users_with_status if user['is_active']]
        elif status_filter == 'inactive':
            resident_users_with_status = [user for user in resident_users_with_status if not user['is_active']]
        
        if resident_users_with_status:
            resident_paginator = Paginator(resident_users_with_status, per_page)
            try:
                resident_page_obj = resident_paginator.page(page_resident)
            except PageNotAnInteger:
                resident_page_obj = resident_paginator.page(1)
            except EmptyPage:
                resident_page_obj = resident_paginator.page(resident_paginator.num_pages)

            user_groups['Residents'] = resident_page_obj
    
    if user_type_filter == 'security' or not user_type_filter:
        security = users.filter(user_type__in=['guard', 'security'])
        # Check profile existence for proper status
        security_users_with_status = []
        for guard in security:
            try:
                guard_profile = SecurityGuard.objects.get(user=guard)
                # Profile exists, check user active status
                is_active_status = guard.is_active and not guard_profile.is_deleted if hasattr(guard_profile, 'is_deleted') else guard.is_active
                security_users_with_status.append({
                    'user': guard,
                    'is_active': is_active_status,
                    'profile_deleted': False
                })
            except SecurityGuard.DoesNotExist:
                # Profile doesn't exist
                security_users_with_status.append({
                    'user': guard,
                    'is_active': False,  # No profile means inactive
                    'profile_deleted': True
                })
        
        # Apply status filter to security users
        if status_filter == 'active':
            security_users_with_status = [user for user in security_users_with_status if user['is_active']]
        elif status_filter == 'inactive':
            security_users_with_status = [user for user in security_users_with_status if not user['is_active']]
        
        if security_users_with_status:
            security_paginator = Paginator(security_users_with_status, per_page)
            try:
                security_page_obj = security_paginator.page(page_security)
            except PageNotAnInteger:
                security_page_obj = security_paginator.page(1)
            except EmptyPage:
                security_page_obj = security_paginator.page(security_paginator.num_pages)

            user_groups['Security Guards'] = security_page_obj
    
    # Get user type statistics - count active profiles only
    admin_count = Admin.objects.count()
    resident_count = Resident.objects.count()
    guard_count = SecurityGuard.objects.count()
    
    # Get total users (including those without profiles)
    admin_users_total = CustomUser.objects.filter(user_type='admin').count()
    resident_users_total = CustomUser.objects.filter(user_type='resident').count()
    guard_users_total = CustomUser.objects.filter(user_type__in=['guard', 'security']).count()
    
    # Calculate deleted counts
    admin_deleted = admin_users_total - admin_count
    resident_deleted = resident_users_total - resident_count
    guard_deleted = guard_users_total - guard_count
    
    # Get active users count
    active_users = CustomUser.objects.filter(is_active=True).count()
    
    # Generate filter description
    filter_description = _get_groups_filter_description(search_query, user_type_filter, status_filter, sort_by)
    
    context = {
        'admin_user': admin_user,
        'user_groups': user_groups,
        'security_guards': user_groups.get('Security Guards', []),
        'total_users': CustomUser.objects.count(),
        'total_residents': resident_count,
        'total_guards': guard_count,
        'total_admins': admin_count,
        'active_users': active_users,
        'search_query': search_query,
        'user_type_filter': user_type_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'filter_description': filter_description,
        'filter_query': filter_query,
        'page_admin': page_admin,
        'page_resident': page_resident,
        'page_security': page_security,
        'per_page': per_page,
    }
    
    return render(request, 'user_groups_enhanced.html', context)


@login_required(login_url='accounts:login')
def users_by_type(request, user_type):
    """View users filtered by type"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Validate user_type
    valid_types = ['admin', 'resident', 'security']
    if user_type not in valid_types:
        messages.error(request, 'Invalid user type')
        return redirect('dashboard:user_groups')
    
    # Get users of specific type (handle both 'guard' and 'security' for security users)
    # Show all users including those without profiles (deleted profiles)
    if user_type == 'security':
        users = CustomUser.objects.filter(user_type__in=['guard', 'security'])
    else:
        users = CustomUser.objects.filter(user_type=user_type)
    
    # Handle case when no users found
    users_with_profiles = []
    if users.exists():
        for user in users:
            profile_info = {
                'user': user,
                'user_type': user.user_type,
                'user_type_display': user.get_user_type_display(),
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'profile_deleted': False,  # Default to False
            }
            
            # Add profile-specific information
            if user_type == 'admin':
                try:
                    profile_info['profile'] = Admin.objects.get(user=user)
                    profile_info['profile_deleted'] = False
                except Admin.DoesNotExist:
                    profile_info['profile'] = None
                    profile_info['profile_deleted'] = True
            elif user_type == 'resident':
                try:
                    profile_info['profile'] = Resident.objects.get(user=user)
                    profile_info['profile_deleted'] = False
                except Resident.DoesNotExist:
                    profile_info['profile'] = None
                    profile_info['profile_deleted'] = True
            elif user_type == 'security':
                # Handle both 'guard' and 'security' user types
                try:
                    profile_info['profile'] = SecurityGuard.objects.get(user=user)
                    profile_info['profile_deleted'] = False
                except SecurityGuard.DoesNotExist:
                    profile_info['profile'] = None
                    profile_info['profile_deleted'] = True
            
            users_with_profiles.append(profile_info)
    
    # Get display name for user type
    user_type_display = {
        'admin': 'Administrators',
        'resident': 'Residents', 
        'security': 'Security Guards'
    }.get(user_type, 'Users')
    
    context = {
        'admin_user': admin_user,
        'users_with_profiles': users_with_profiles,
        'user_type': user_type,
        'user_type_display': user_type_display,
        'total_count': users.count(),
    }
    
    return render(request, 'users_by_type_enhanced.html', context)

"""
@login_required(login_url='accounts:login')
def enhanced_user_groups(request):
     #Enhanced user groups view with complete context
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    from django.contrib.auth.models import Group
    
    # Get all groups with user counts and permissions
    all_groups = []
    for group in Group.objects.all():
        all_groups.append({
            'id': group.id,
            'name': group.name,
            'user_count': group.user_set.count(),
            'permissions_count': group.permissions.count()
        }) 
    
    # Get complete user-group mapping
    user_group_mappings = []
    for user in CustomUser.objects.all():
        for group in user.groups.all():
            user_group_mappings.append({
                'user': user,
                'group': group
            })
    
    # Calculate statistics
    total_users = CustomUser.objects.count()
    users_with_groups = CustomUser.objects.filter(groups__isnull=False).distinct().count()
    users_without_groups = total_users - users_with_groups
    users_without_groups_list = CustomUser.objects.filter(groups__isnull=True)
    
    context = {
        'admin_user': admin_user,
        'all_groups': all_groups,
        'user_group_mappings': user_group_mappings,
        'total_users': total_users,
        'users_with_groups': users_with_groups,
        'users_without_groups': users_without_groups,
        'users_without_groups_list': users_without_groups_list,
        'total_groups': Group.objects.count(),
        'total_mappings': len(user_group_mappings),
    }
    
    return render(request, 'enhanced_user_groups.html', context) """


@login_required(login_url='accounts:login')
def reports(request):
    """Main reports view with enhanced statistics"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = timezone.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    # Get comprehensive statistics
    visitor_stats = {
        'total': Visitor.objects.count(),
        'today': Visitor.objects.filter(entry_time__date=timezone.now().date()).count(),
        'this_week': Visitor.objects.filter(
            entry_time__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'active': Visitor.objects.filter(exit_time__isnull=True).count(),
        'last_updated': timezone.now(),
    }
    
    activity_stats = SystemAudit.objects.aggregate(
        total=Count('id'),
        today=Count('id', filter=Q(timestamp__date=timezone.now().date())),
        this_week=Count('id', filter=Q(timestamp__gte=timezone.now() - timedelta(days=7))),
        this_month=Count('id', filter=Q(timestamp__gte=timezone.now() - timedelta(days=30)))
    )
    
    gate_pass_stats = GatePass.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='approved')),
        expired=Count('id', filter=Q(status='rejected')),
        today=Count('id', filter=Q(issue_time__date=timezone.now().date())),
        last_updated=timezone.now(),
    )
    
    audit_stats = SystemAudit.objects.aggregate(
        total=Count('id'),
        today=Count('id', filter=Q(timestamp__date=timezone.now().date())),
        this_week=Count('id', filter=Q(timestamp__gte=timezone.now() - timedelta(days=7))),
        this_month=Count('id', filter=Q(timestamp__gte=timezone.now() - timedelta(days=30)))
    )
    
    # Calculate total reports
    total_reports = (
        visitor_stats['total'] + 
        activity_stats['total'] + 
        gate_pass_stats['total'] + 
        audit_stats['total']
    )
    
    # Get statistics for the date range
    range_visitor_stats = Visitor.objects.filter(
        entry_time__date__gte=start_date,
        entry_time__date__lte=end_date
    ).aggregate(
        total=Count('id'),
        unique_visitors=Count('visitor_name', distinct=True),
        by_purpose=Count('purpose')
    )
    
    # Get daily visitor counts
    daily_visitors = []
    current_date = start_date
    while current_date <= end_date:
        count = Visitor.objects.filter(entry_time__date=current_date).count()
        daily_visitors.append({
            'date': current_date,
            'count': count
        })
        current_date += timedelta(days=1)

    context = {
        'admin_user': admin_user,
        'start_date': start_date,
        'end_date': end_date,
        'visitor_stats': visitor_stats,
        'activity_stats': activity_stats,
        'gate_pass_stats': gate_pass_stats,
        'audit_stats': audit_stats,
        'total_reports': total_reports,
        'range_visitor_stats': range_visitor_stats,
        'daily_visitors': daily_visitors,
    }

    return render(request, 'reports_enhanced.html', context)


@login_required(login_url='accounts:login')
def visitor_reports(request):
    """Detailed visitor reports"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    # First, try to get actual visitor records
    visitors = Visitor.objects.all()
    
    # Apply date filters to actual visitors
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        visitors = visitors.filter(entry_time__date__gte=start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        visitors = visitors.filter(entry_time__date__lte=end_date)
    
    # Process actual visitor records
    visitors_with_history = []
    for visitor in visitors.order_by('-entry_time'):
        history = VisitorHistory.objects.filter(visitor=visitor).first()
        visitor_data = {
            'visitor': visitor,
            'status': history.status if history else 'unknown',
            'entry_time': visitor.entry_time,
            'exit_time': history.exit_time if history else visitor.exit_time,
            'audit_user': 'N/A',  # Not available for actual visitors
            'audit_timestamp': visitor.created_at,
        }
        visitors_with_history.append(visitor_data)
    
    # If no actual visitors found, fall back to audit data
    if not visitors_with_history:
        from audit.models import SystemAudit
        activities = SystemAudit.objects.filter(
            action_type__in=['visitor_register', 'visitor_exit']
        )
        
        # Apply date filters to audit activities
        if start_date:
            activities = activities.filter(timestamp__date__gte=start_date)
        
        if end_date:
            activities = activities.filter(timestamp__date__lte=end_date)
        
        # Apply status filter (map to action types)
        if status and status.strip():
            if status == 'pending':
                activities = activities.filter(action_type='visitor_register')
            elif status == 'exited':
                activities = activities.filter(action_type='visitor_exit')
            elif status == 'approved':
                activities = activities.filter(action_type='visitor_register')
            else:
                activities = activities.filter(action_type__in=['visitor_register', 'visitor_exit'])
        
        # Process activities to visitor-like data
        for activity in activities.order_by('-timestamp'):
            # Extract visitor name from description
            visitor_name = activity.description.replace('Visitor ', '').replace(' registered', '').replace(' marked exit', '')
            
            # Create a mock resident object
            mock_resident = type('Resident', (), {
                'flat_number': 'N/A',
                'user': type('User', (), {
                    'get_full_name': lambda: 'N/A'
                })()
            })()
            
            visitor_data = {
                'visitor': type('Visitor', (), {
                    'visitor_name': visitor_name,
                    'mobile_number': 'N/A',
                    'purpose': 'N/A',
                    'resident': mock_resident,
                    'entry_time': activity.timestamp if activity.action_type == 'visitor_register' else None,
                    'exit_time': activity.timestamp if activity.action_type == 'visitor_exit' else None,
                })(),
                'status': 'registered' if activity.action_type == 'visitor_register' else 'exited',
                'entry_time': activity.timestamp if activity.action_type == 'visitor_register' else None,
                'exit_time': activity.timestamp if activity.action_type == 'visitor_exit' else None,
                'audit_user': activity.user.username if activity.user else 'Unknown',
                'audit_timestamp': activity.timestamp,
            }
            visitors_with_history.append(visitor_data)
    
    # Handle export parameter
    if request.GET.get('export') == 'true':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visitor_reports.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Visitor Name', 'Entry Time', 'Exit Time', 'Status', 'Purpose', 'Resident'])
        
        for visitor_data in visitors_with_history:
            visitor = visitor_data.get('visitor')
            resident = visitor_data.get('resident')
            writer.writerow([
                visitor.visitor_name if visitor else 'N/A',
                visitor_data.get('entry_time', 'N/A'),
                visitor_data.get('exit_time', 'N/A'),
                visitor_data.get('status', 'N/A'),
                visitor.purpose if visitor else 'N/A',
                resident.user.get_full_name() if resident and resident.user else 'N/A'
            ])
        
        return response
    
    context = {
        'admin_user': admin_user,
        'visitors_with_history': visitors_with_history,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'total_visitors': len(visitors_with_history),
    }
    
    return render(request, 'visitor_reports_enhanced.html', context)


@login_required(login_url='accounts:login')
def activity_reports(request):
    """System activity reports"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    action_type = request.GET.get('action_type')
    
    activities = SystemAudit.objects.all()
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        activities = activities.filter(timestamp__date__gte=start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        activities = activities.filter(timestamp__date__lte=end_date)
    
    if action_type:
        activities = activities.filter(action_type=action_type)

    activities = activities.order_by('-timestamp')
    act_paginator = Paginator(activities, 20)
    act_page = request.GET.get('page', 1)
    try:
        act_page = int(act_page)
    except (TypeError, ValueError):
        act_page = 1
    try:
        activities_page = act_paginator.page(act_page)
    except PageNotAnInteger:
        activities_page = act_paginator.page(1)
    except EmptyPage:
        activities_page = act_paginator.page(act_paginator.num_pages)

    act_nav = request.GET.copy()
    act_nav.pop('page', None)
    activity_filter_query = act_nav.urlencode()

    context = {
        'admin_user': admin_user,
        'activities': activities_page,
        'activities_page': activities_page,
        'start_date': start_date,
        'end_date': end_date,
        'action_type': action_type,
        'action_types': SystemAudit.ACTION_TYPES,
        'activity_filter_query': activity_filter_query,
    }

    return render(request, 'activity_reports_enhanced.html', context)


@admin_required
def dashboard_settings(request):
    """Dashboard settings"""
    if request.method == 'POST':
        # Handle settings update
        settings_obj = DashboardSettings.get_settings()
        
        try:
            otp_expiry = int(request.POST.get('otp_expiry', '5'))
            if otp_expiry < 1 or otp_expiry > 60:
                otp_expiry = 5
        except ValueError:
            otp_expiry = 5
        
        try:
            max_attempts = int(request.POST.get('max_attempts', '3'))
            if max_attempts < 1 or max_attempts > 10:
                max_attempts = 3
        except ValueError:
            max_attempts = 3
        
        try:
            cleanup_days = int(request.POST.get('auto_cleanup_days', '30'))
            if cleanup_days < 1 or cleanup_days > 365:
                cleanup_days = 30
        except ValueError:
            cleanup_days = 30
        
        settings_obj.otp_expiry_minutes = otp_expiry
        settings_obj.max_otp_attempts = max_attempts
        settings_obj.enable_notifications = request.POST.get('enable_notifications') == 'on'
        settings_obj.auto_cleanup_days = cleanup_days
        
        try:
            items_per_page = int(request.POST.get('items_per_page', '10'))
            if items_per_page < 5 or items_per_page > 100:
                items_per_page = 10
        except ValueError:
            items_per_page = 10
        
        settings_obj.items_per_page = items_per_page
        
        settings_obj.save()
        
        messages.success(request, f'Settings updated successfully!')
        return redirect('dashboard:dashboard_settings')
    
    # Get current settings
    settings_obj = DashboardSettings.get_settings()
    
    context = {
        'admin_user': request.admin_user,
        'settings': settings_obj,
    }
    
    return render(request, 'settings.html', context)


def get_group_color(group_name):
    """Get color for group badge"""
    colors = {
        'Administrators': 'danger',
        'Security Guards': 'warning',
        'Residents': 'success'
    }
    return colors.get(group_name, 'secondary')


def _get_admin_filter_description(search, action_type, status, start_date, end_date):
    """Generate human-readable filter description for admin dashboard"""
    descriptions = []
    
    if search:
        descriptions.append(f"Search: '{search}'")
    
    if action_type and action_type != 'all':
        for action_value, action_label in SystemAudit.ACTION_TYPES:
            if action_value == action_type:
                descriptions.append(f"Action: {action_label}")
                break
    
    if status and status != 'all':
        for status_value, status_label in SystemAudit.STATUS_TYPES:
            if status_value == status:
                descriptions.append(f"Status: {status_label}")
                break
    
    if start_date:
        try:
            parsed_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%B %d, %Y')
            descriptions.append(f"From: {parsed_date}")
        except:
            descriptions.append(f"From: {start_date}")
    
    if end_date:
        try:
            parsed_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%B %d, %Y')
            descriptions.append(f"To: {parsed_date}")
        except:
            descriptions.append(f"To: {end_date}")
    
    if descriptions:
        return " | ".join(descriptions)
    else:
        return "No filters applied"


def _get_groups_filter_description(search, user_type, status, sort_by):
    """Generate human-readable filter description for user groups"""
    descriptions = []
    
    if search:
        descriptions.append(f"Search: '{search}'")
    
    if user_type:
        type_display = {
            'admin': 'Administrators',
            'resident': 'Residents', 
            'security': 'Security Guards'
        }.get(user_type, user_type.title())
        descriptions.append(f"Type: {type_display}")
    
    if status:
        descriptions.append(f"Status: {status.title()}")
    
    if sort_by:
        sort_display = {
            'username': 'Username',
            'name': 'Full Name',
            'date_joined': 'Date Joined',
            'last_login': 'Last Login'
        }.get(sort_by, sort_by.title())
        descriptions.append(f"Sort: {sort_display}")
    
    if descriptions:
        return " | ".join(descriptions)
    else:
        return "No filters applied"


@login_required(login_url='accounts:login')
def export_reports(request):
    """Export all reports data to CSV"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="system_reports.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Report Type', 'Total Count', 'Active Count', 'Date Generated'])
    
    # Get statistics
    visitor_stats = Visitor.objects.count()
    active_visitors = Visitor.objects.filter(exit_time__isnull=True).count()
    writer.writerow(['Visitors', visitor_stats, active_visitors, timezone.now().date()])
    
    admin_count = Admin.objects.count()
    writer.writerow(['Administrators', admin_count, admin_count, timezone.now().date()])
    
    resident_count = Resident.objects.count()
    writer.writerow(['Residents', resident_count, resident_count, timezone.now().date()])
    
    guard_count = SecurityGuard.objects.count()
    writer.writerow(['Security Guards', guard_count, guard_count, timezone.now().date()])
    
    activity_count = SystemAudit.objects.count()
    writer.writerow(['System Activities', activity_count, activity_count, timezone.now().date()])
    
    return response


@login_required(login_url='accounts:login')
def gate_pass_reports(request):
    """Gate pass reports view"""
    # Check if user is admin first
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return redirect('home')
    
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = timezone.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    # Get gate pass statistics
    gate_passes = GatePass.objects.filter(
        issue_time__date__gte=start_date,
        issue_time__date__lte=end_date
    )
    
    context = {
        'admin_user': admin_user,
        'gate_passes': gate_passes,
        'start_date': start_date,
        'end_date': end_date,
        'total_passes': gate_passes.count(),
        'approved_passes': gate_passes.filter(status='approved').count(),
        'rejected_passes': gate_passes.filter(status='rejected').count(),
        'pending_passes': gate_passes.filter(status='pending').count(),
        'expired_passes': gate_passes.filter(valid_till__lt=timezone.now()).count(),
    }
    
    return render(request, 'gate_pass_reports_enhanced.html', context)


@method_decorator(login_required(login_url='accounts:login'), name='dispatch')
class UserDetailAPI(View):
    """API endpoint to get user details for modal display"""
    
    def get(self, request, user_id):
        try:
            # Check if user is admin
            if not request.user.is_authenticated or request.user.user_type != 'admin':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            
            # Try to get user details
            try:
                user = CustomUser.objects.get(id=user_id)
                
                # Get profile information based on user type
                profile_info = {}
                profile_status = 'No Profile'
                profile_deleted = False
                
                if user.user_type == 'admin':
                    try:
                        admin = Admin.objects.get(user=user)
                        profile_info = {
                            'department': admin.department or 'N/A',
                            'admin_id': admin.admin_id or 'N/A',
                            'phone': admin.phone_number or 'N/A',
                        }
                        profile_status = 'Active'
                    except Admin.DoesNotExist:
                        profile_deleted = True
                        profile_status = 'Deleted'
                        
                elif user.user_type == 'resident':
                    try:
                        resident = Resident.objects.get(user=user)
                        profile_info = {
                            'flat_number': resident.flat_number or 'N/A',
                            'building_name': resident.building_name or 'N/A',
                            'phone': resident.phone_number or 'N/A',
                        }
                        profile_status = 'Active'
                    except Resident.DoesNotExist:
                        profile_deleted = True
                        profile_status = 'Deleted'
                        
                elif user.user_type in ['guard', 'security']:
                    try:
                        guard = SecurityGuard.objects.get(user=user)
                        profile_info = {
                            'employee_id': guard.employee_id or 'N/A',
                            'shift': guard.shift or 'N/A',
                            'phone': guard.phone_number or 'N/A',
                        }
                        profile_status = 'Active'
                    except SecurityGuard.DoesNotExist:
                        profile_deleted = True
                        profile_status = 'Deleted'
                
                # Format data for response
                data = {
                    'success': True,
                    'user_id': user.id,
                    'username': user.username,
                    'first_name': user.first_name or 'N/A',
                    'last_name': user.last_name or 'N/A',
                    'full_name': user.get_full_name() or 'N/A',
                    'email': user.email or 'N/A',
                    'user_type': user.user_type or 'N/A',
                    'is_active': user.is_active,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else 'N/A',
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never',
                    'profile_status': profile_status,
                    'profile_deleted': profile_deleted,
                    'profile_info': profile_info,
                }
                
                return JsonResponse(data)
                
            except CustomUser.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(login_required(login_url='accounts:login'), name='dispatch')
class VisitorDetailAPI(View):
    """API endpoint to get visitor details for modal display"""
    
    def get(self, request, visitor_id):
        try:
            # Check if user is admin
            if not request.user.is_authenticated or request.user.user_type != 'admin':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            
            # Try to get visitor details
            try:
                visitor = Visitor.objects.get(id=visitor_id)
                
                # Calculate duration if both times exist
                duration = 'N/A'
                if visitor.entry_time and visitor.exit_time:
                    duration = str(visitor.exit_time - visitor.entry_time).split('.')[0]
                
                data = {
                    'success': True,
                    'visitor_name': visitor.visitor_name,
                    'mobile_number': visitor.mobile_number or 'N/A',
                    'purpose': visitor.purpose or 'N/A',
                    'status': 'Completed' if visitor.exit_time else 'Active',
                    'entry_time': visitor.entry_time.strftime('%Y-%m-%d %H:%M:%S') if visitor.entry_time else 'N/A',
                    'exit_time': visitor.exit_time.strftime('%Y-%m-%d %H:%M:%S') if visitor.exit_time else 'N/A',
                    'duration': duration,
                    'host_name': f"{visitor.resident.user.get_full_name()} ({visitor.resident.flat_number})" if visitor.resident else 'N/A',
                    'created_at': visitor.created_at.strftime('%Y-%m-%d %H:%M:%S') if visitor.created_at else 'N/A',
                }
                
                return JsonResponse(data)
                
            except Visitor.DoesNotExist:
                # If visitor doesn't exist, check if it's an audit record
                try:
                    audit_record = SystemAudit.objects.filter(
                        action_type__in=['visitor_register', 'visitor_exit'],
                        description__icontains=str(visitor_id)
                    ).first()
                    
                    if audit_record:
                        return JsonResponse({
                            'success': False,
                            'error': 'Audit record found',
                            'audit_description': audit_record.description,
                            'audit_timestamp': audit_record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'audit_user': audit_record.user.username if audit_record.user else 'System'
                        })
                    else:
                        return JsonResponse({'success': False, 'error': 'Visitor not found'})
                        
                except Exception:
                    return JsonResponse({'success': False, 'error': 'Visitor not found'})
                    
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
