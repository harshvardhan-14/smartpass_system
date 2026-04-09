"""
URL configuration for GatePass System project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    
    # App URLs
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('visitors/', include('visitors.urls', namespace='visitors')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('audit/', include('audit.urls', namespace='audit')),
]

#serves static files and media with proper url pattern
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
