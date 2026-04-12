from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_dashboard, name='audit_dashboard'),
    path('logs/', views.audit_logs, name='audit_logs'),
    path('logs/<str:action_type>/', views.audit_logs_by_type, name='audit_logs_by_type'),
    path('search/', views.search_audit_logs, name='search_audit_logs'),
    path('export/', views.export_audit_data, name='export_audit_data'),
    path('api/activity-details/<int:activity_id>/', views.activity_details_api, name='activity_details_api'),
]
