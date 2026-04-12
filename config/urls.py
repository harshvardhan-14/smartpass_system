"""
Main URL configuration – all routes are under /api/v1/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny


# ─── Swagger / OpenAPI ─────────────────────────────────────────────────────────
schema_view = get_schema_view(
    openapi.Info(
        title='Smart Gate Pass System API',
        default_version='v1',
        description=(
            'Production-ready REST API for the Smart Gate Pass System. '
            'Authenticate using JWT Bearer tokens.'
        ),
        contact=openapi.Contact(email='admin@gatepass.local'),
    ),
    public=True,
    permission_classes=[AllowAny],
)


class APIRootView(APIView):
    """
    GET /api/v1/
    Lists all top-level API groups.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'version': 'v1',
            'endpoints': {
                'auth': request.build_absolute_uri('/api/v1/auth/login/'),
                'accounts': request.build_absolute_uri('/api/v1/accounts/me/'),
                'visitors': request.build_absolute_uri('/api/v1/visitors/'),
                'dashboard': request.build_absolute_uri('/api/v1/dashboard/'),
                'audit': request.build_absolute_uri('/api/v1/audit/'),
                'docs': request.build_absolute_uri('/api/docs/'),
                'redoc': request.build_absolute_uri('/api/redoc/'),
            },
        })


urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API root
    path('api/v1/', APIRootView.as_view(), name='api_root'),

    # App APIs (namespaced inside accounts urls for auth + accounts)
    path('api/v1/', include('accounts.urls', namespace='accounts')),
    path('api/v1/visitors/', include('visitors.urls', namespace='visitors')),
    path('api/v1/dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('api/v1/audit/', include('audit.urls', namespace='audit')),

    # Swagger / ReDoc
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema_swagger_ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema_redoc'),
    path('api/schema.json', schema_view.without_ui(cache_timeout=0), name='schema_json'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
