"""
URL configuration – serves BOTH HTML template views AND the DRF REST API.

Template routes (browser / HTML):
    /                  home
    /accounts/         login, register, profile …
    /visitors/         dashboard, register visitor, OTP, gate pass …
    /dashboard/        admin dashboard, reports, settings …
    /audit/            audit logs, export …

REST API routes (JWT / JSON):
    /api/v1/auth/      login, logout, token refresh, password reset
    /api/v1/accounts/  register, me, profile
    /api/v1/visitors/  visitor CRUD, OTP, gate passes, dashboard
    /api/v1/dashboard/ admin stats, user mgmt, reports
    /api/v1/audit/     audit logs, export
    /api/docs/         Swagger UI
    /api/redoc/        ReDoc UI
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.views import home


# ─── Swagger / ReDoc ──────────────────────────────────────────────────────────
schema_view = get_schema_view(
    openapi.Info(
        title='Smart Gate Pass System API',
        default_version='v1',
        description='JWT-authenticated REST API for the Smart Gate Pass System.',
    ),
    public=True,
    permission_classes=[AllowAny],
)


class APIRootView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'version': 'v1',
            'docs': request.build_absolute_uri('/api/docs/'),
            'redoc': request.build_absolute_uri('/api/redoc/'),
        })


urlpatterns = [
    # ── Django admin ────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Template (HTML) routes ───────────────────────────────────────────────
    path('', home, name='home'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('visitors/', include('visitors.urls', namespace='visitors')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('audit/', include('audit.urls', namespace='audit')),

    # ── REST API routes ──────────────────────────────────────────────────────
    path('api/v1/', APIRootView.as_view(), name='api_root'),
    path('api/v1/', include('accounts.api_urls', namespace='accounts_api')),
    path('api/v1/visitors/', include('visitors.api_urls', namespace='visitors_api')),
    path('api/v1/dashboard/', include('dashboard.api_urls', namespace='dashboard_api')),
    path('api/v1/audit/', include('audit.api_urls', namespace='audit_api')),

    # ── API docs ─────────────────────────────────────────────────────────────
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema_swagger_ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema_redoc'),
    path('api/schema.json', schema_view.without_ui(cache_timeout=0), name='schema_json'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
