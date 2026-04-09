from django.urls import path
from . import views

app_name = 'visitors'

urlpatterns = [
    # Visitor Management
    path('register/', views.register_visitor, name='register_visitor'),
    path('verify-otp/<int:visitor_id>/', views.verify_otp, name='verify_otp'),
    path('mark-exit/<int:visitor_id>/', views.mark_exit, name='mark_exit'),
    path('detail/<int:visitor_id>/', views.visitor_detail, name='visitor_detail'),
    
    # Gate Pass
    path('gate-pass/<int:pass_id>/', views.gate_pass_details, name='gate_pass_details'),
    
    # History
    path('history/', views.visitor_history, name='visitor_history'),
    
    # List
    path('list/', views.visitor_list, name='visitor_list'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='visitor_dashboard'),
    
    # API
    path('api/search-residents/', views.search_residents, name='search_residents'),
]
