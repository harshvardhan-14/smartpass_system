from django.urls import path
from . import views

app_name = 'visitors'

urlpatterns = [
    # Visitors
    path('', views.VisitorListCreateView.as_view(), name='visitor_list_create'),
    path('<int:visitor_id>/', views.VisitorDetailView.as_view(), name='visitor_detail'),
    path('<int:visitor_id>/verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('<int:visitor_id>/mark-exit/', views.MarkExitView.as_view(), name='mark_exit'),

    # Gate Passes
    path('gate-passes/', views.GatePassListView.as_view(), name='gate_pass_list'),
    path('gate-passes/<int:pass_id>/', views.GatePassDetailView.as_view(), name='gate_pass_detail'),

    # Dashboard & History
    path('dashboard/', views.VisitorDashboardView.as_view(), name='visitor_dashboard'),
    path('history/', views.VisitorHistoryView.as_view(), name='visitor_history'),

    # Resident search
    path('search-residents/', views.ResidentSearchView.as_view(), name='search_residents'),
]
