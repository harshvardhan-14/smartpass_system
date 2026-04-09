from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Password Reset
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<int:user_id>/', views.reset_password_verify, name='reset_password_verify'),
    
    # Registration
    path('register/resident/', views.register_resident, name='register_resident'),
    path('register/guard/', views.register_security_guard, name='register_guard'),
    path('register/guard-simple/', views.register_security_guard_simple, name='register_guard_simple'),
    
    # User Management
    path('profile/', views.user_profile, name='user_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    
    # Home
    path('', views.home, name='home'),
]
