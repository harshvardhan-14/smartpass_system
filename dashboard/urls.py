from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Admin Dashboard
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
    path('users/', views.user_groups, name='user_groups'),
    path('users/<str:user_type>/', views.users_by_type, name='users_by_type'),
    #path('enhanced-users/', views.enhanced_user_groups, name='enhanced_user_groups'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/visitors/', views.visitor_reports, name='visitor_reports'),
    path('reports/activity/', views.activity_reports, name='activity_reports'),
    path('reports/export/', views.export_reports, name='export_reports'),
    path('reports/gate-pass/', views.gate_pass_reports, name='gate_pass_reports'),
    
    # API Endpoints
    path('api/visitor-detail/<int:visitor_id>/', views.VisitorDetailAPI.as_view(), name='visitor_detail_api'),
    path('api/user-detail/<int:user_id>/', views.UserDetailAPI.as_view(), name='user_detail_api'),
    
    # Settings
    path('settings/', views.dashboard_settings, name='dashboard_settings'),
]
