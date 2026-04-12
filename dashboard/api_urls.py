from django.urls import path
from . import api_views as views

app_name = 'dashboard_api'

urlpatterns = [
    # Dashboard overview
    path('', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:user_id>/', views.UserDetailAdminView.as_view(), name='user_detail'),

    # Reports
    path('reports/visitors/', views.VisitorReportsView.as_view(), name='visitor_reports'),
    path('reports/activity/', views.ActivityReportsView.as_view(), name='activity_reports'),
    path('reports/gate-passes/', views.GatePassReportsView.as_view(), name='gate_pass_reports'),
    path('reports/export/', views.ExportReportsView.as_view(), name='export_reports'),

    # Settings
    path('settings/', views.DashboardSettingsView.as_view(), name='dashboard_settings'),
]
