from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api_views as views

app_name = 'accounts_api'

urlpatterns = [
    # Auth
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/<int:user_id>/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Registration
    path('accounts/register/resident/', views.RegisterResidentView.as_view(), name='register_resident'),
    path('accounts/register/guard/', views.RegisterSecurityGuardView.as_view(), name='register_guard'),

    # Profile
    path('accounts/me/', views.MeView.as_view(), name='me'),
    path('accounts/profile/', views.ProfileView.as_view(), name='profile'),
]
