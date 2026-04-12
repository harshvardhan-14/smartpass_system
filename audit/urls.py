from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.AuditDashboardView.as_view(), name='audit_dashboard'),
    path('logs/', views.AuditLogListView.as_view(), name='audit_logs'),
    path('logs/<int:activity_id>/', views.AuditLogDetailView.as_view(), name='audit_log_detail'),
    path('export/', views.AuditExportView.as_view(), name='audit_export'),
]
