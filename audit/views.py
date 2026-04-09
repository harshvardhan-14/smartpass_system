from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SystemAudit
from accounts.models import CustomUser, Admin
from django.core.paginator import Paginator
from django.http import JsonResponse
import csv
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@login_required(login_url='accounts:login')
def audit_dashboard(request):
    """Audit dashboard with statistics and recent activities"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get statistics
    total_activities = SystemAudit.objects.count()
    
    # Get activity counts by type
    activity_counts = {}
    for action_type, display_name in SystemAudit.ACTION_TYPES:
        count = SystemAudit.objects.filter(action_type=action_type).count()
        if count > 0:
            activity_counts[action_type] = {
                'display_name': display_name,
                'count': count
            }
    
    # Get recent activities
    recent_activities = SystemAudit.objects.all().order_by('-timestamp')[:20]
    
    # Get failed activities (for security monitoring)
    failed_activities = SystemAudit.objects.filter(status='failure').order_by('-timestamp')[:10]
    
    # Get today's activities
    today = timezone.now().date()
    today_activities = SystemAudit.objects.filter(timestamp__date=today).count()
    
    # Get user activity summary
    user_activity_summary = {}
    recent_users = CustomUser.objects.filter(
        audit_logs__timestamp__gte=timezone.now() - timedelta(days=7)
    ).distinct()
    
    for user in recent_users:
        activity_count = SystemAudit.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        user_activity_summary[user] = activity_count
    
    context = {
        'admin_user': admin_user,
        'total_activities': total_activities,
        'activity_counts': activity_counts,
        'recent_activities': recent_activities,
        'failed_activities': failed_activities,
        'today_activities': today_activities,
        'user_activity_summary': user_activity_summary,
    }
    
    return render(request, 'audit_dashboard.html', context)


@login_required(login_url='accounts:login')
def audit_logs(request):
    """Comprehensive audit logs with filtering"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    action_type = request.GET.get('action_type', '')
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    ip_filter = request.GET.get('ip', '')
    
    # Base queryset
    activities = SystemAudit.objects.all()
    
    # Apply search filter
    if search_query:
        activities = activities.filter(
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user_agent__icontains=search_query) |
            Q(target_model__icontains=search_query)
        )
    
    # Apply action type filter
    if action_type and action_type != 'all':
        activities = activities.filter(action_type=action_type)
    
    # Apply status filter
    if status_filter and status_filter != 'all':
        activities = activities.filter(status=status_filter)
    
    # Apply user filter
    if user_filter and user_filter != 'all':
        try:
            user_id = int(user_filter)
            activities = activities.filter(user_id=user_id)
        except ValueError:
            pass
    
    # Apply date filters
    if start_date:
        try:
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=start_date_parsed)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=end_date_parsed)
        except ValueError:
            pass
    
    # Apply IP filter
    if ip_filter:
        activities = activities.filter(ip_address__icontains=ip_filter)
    
    # Get total activities count (before filtering)
    total_activities_count = SystemAudit.objects.count()
    
    # Order by timestamp (most recent first)
    activities = activities.order_by('-timestamp')
    
    # Get filter options
    action_types = SystemAudit.ACTION_TYPES
    status_types = SystemAudit.STATUS_TYPES
    users = CustomUser.objects.filter(audit_logs__isnull=False).distinct()
    
    # Pagination - Show only 10 entries per page
    paginator = Paginator(activities, 10)  # 10 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin_user': admin_user,
        'activities': page_obj,
        'action_types': action_types,
        'status_types': status_types,
        'users': users,
        'search_query': search_query,
        'action_type': action_type,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'start_date': start_date,
        'end_date': end_date,
        'ip_filter': ip_filter,
        'filter_description': _get_audit_filter_description(search_query, action_type, status_filter, user_filter, start_date, end_date, ip_filter),
        'total_activities': total_activities_count,
    }
    
    return render(request, 'audit_logs.html', context)


@login_required(login_url='accounts:login')
def audit_logs_by_type(request, action_type):
    """Audit logs filtered by specific action type"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Validate action type
    valid_types = [choice[0] for choice in SystemAudit.ACTION_TYPES]
    if action_type not in valid_types:
        return redirect('audit:audit_logs')
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Base queryset filtered by action type
    activities = SystemAudit.objects.filter(action_type=action_type)
    
    # Apply other filters
    if search_query:
        activities = activities.filter(
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    if status_filter and status_filter != 'all':
        activities = activities.filter(status=status_filter)
    
    if user_filter and user_filter != 'all':
        try:
            user_id = int(user_filter)
            activities = activities.filter(user_id=user_id)
        except ValueError:
            pass
    
    if start_date:
        try:
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=start_date_parsed)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=end_date_parsed)
        except ValueError:
            pass
    
    activities = activities.order_by('-timestamp')
    
    # Get filter options
    status_types = SystemAudit.STATUS_TYPES
    users = CustomUser.objects.filter(audit_logs__isnull=False).distinct()
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin_user': admin_user,
        'activities': page_obj,
        'action_type': action_type,
        'action_type_display': dict(SystemAudit.ACTION_TYPES).get(action_type, action_type),
        'status_types': status_types,
        'users': users,
        'search_query': search_query,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'start_date': start_date,
        'end_date': end_date,
        'filter_description': _get_audit_filter_description(search_query, action_type, status_filter, user_filter, start_date, end_date, ''),
        'total_activities': activities.count(),
    }
    
    return render(request, 'audit_logs_by_type.html', context)


@login_required(login_url='accounts:login')
def search_audit_logs(request):
    """Search audit logs with advanced search"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    search_query = request.GET.get('q', '').strip()
    
    if not search_query:
        return redirect('audit:audit_logs')
    
    # Advanced search across multiple fields
    activities = SystemAudit.objects.filter(
        Q(description__icontains=search_query) |
        Q(user__username__icontains=search_query) |
        Q(user__first_name__icontains=search_query) |
        Q(user__last_name__icontains=search_query) |
        Q(user_agent__icontains=search_query) |
        Q(target_model__icontains=search_query) |
        Q(ip_address__icontains=search_query)
    ).order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin_user': admin_user,
        'activities': page_obj,
        'search_query': search_query,
        'total_activities': activities.count(),
        'filter_description': f"Search: '{search_query}'",
    }
    
    return render(request, 'audit_search_results.html', context)


@login_required(login_url='accounts:login')
def export_audit_data(request):
    """Export audit data to CSV"""
    try:
        admin_user = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return redirect('home')
    
    # Get filter parameters (same as audit_logs)
    search_query = request.GET.get('search', '').strip()
    action_type = request.GET.get('action_type', '')
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Build queryset with filters
    activities = SystemAudit.objects.all()
    
    if search_query:
        activities = activities.filter(description__icontains=search_query)
    
    if action_type and action_type != 'all':
        activities = activities.filter(action_type=action_type)
    
    if status_filter and status_filter != 'all':
        activities = activities.filter(status=status_filter)
    
    if user_filter and user_filter != 'all':
        try:
            user_id = int(user_filter)
            activities = activities.filter(user_id=user_id)
        except ValueError:
            pass
    
    if start_date:
        try:
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=start_date_parsed)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=end_date_parsed)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'User', 'Action Type', 'Description', 'Status', 
        'IP Address', 'Target Model', 'Target ID', 'User Agent'
    ])
    
    for activity in activities.order_by('-timestamp'):
        writer.writerow([
            activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            activity.user.username if activity.user else 'Anonymous',
            activity.get_action_type_display(),
            activity.description,
            activity.get_status_display(),
            activity.ip_address or '',
            activity.target_model or '',
            activity.target_id or '',
            activity.user_agent[:100] if activity.user_agent else ''
        ])
    
    return response


def _get_audit_filter_description(search, action_type, status, user, start_date, end_date, ip):
    """Generate human-readable filter description for audit logs"""
    descriptions = []
    
    if search:
        descriptions.append(f"Search: '{search}'")
    
    if action_type and action_type != 'all':
        action_display = dict(SystemAudit.ACTION_TYPES).get(action_type, action_type)
        descriptions.append(f"Action: {action_display}")
    
    if status and status != 'all':
        status_display = dict(SystemAudit.STATUS_TYPES).get(status, status.title())
        descriptions.append(f"Status: {status_display}")
    
    if user and user != 'all':
        try:
            user_obj = CustomUser.objects.get(id=int(user))
            descriptions.append(f"User: {user_obj.get_full_name()}")
        except:
            descriptions.append(f"User: {user}")
    
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
    
    if ip:
        descriptions.append(f"IP: {ip}")
    
    if descriptions:
        return " | ".join(descriptions)
    else:
        return "No filters applied"


@csrf_exempt
@login_required(login_url='accounts:login')
def activity_details_api(request, activity_id):
    """API endpoint to get detailed activity information"""
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        activity = SystemAudit.objects.get(id=activity_id)
        
        # Format the activity details
        details = {
            'success': True,
            'id': activity.id,
            'user': {
                'id': activity.user.id,
                'username': activity.user.username,
                'full_name': f"{activity.user.first_name} {activity.user.last_name}".strip() or activity.user.username,
                'email': activity.user.email,
                'user_type': getattr(activity.user, 'user_type', 'N/A')
            },
            'action_type': activity.action_type,
            'action_display': activity.get_action_type_display(),
            'description': activity.description,
            'status': activity.status,
            'status_display': activity.get_status_display(),
            'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': activity.ip_address or 'N/A',
            'user_agent': activity.user_agent or 'N/A',
            'target_model': activity.target_model or 'N/A',
            'target_id': activity.target_id or 'N/A',
            'old_values': activity.old_values or {},
            'new_values': activity.new_values or {},
        }
        
        return JsonResponse(details)
        
    except SystemAudit.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Activity not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
