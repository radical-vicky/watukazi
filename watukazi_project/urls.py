"""
URL configuration for watukazi_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('home.urls')),  # Add this line - home app should come before accounts
    path('', include('accounts.urls')),  # Keep this but note it might override home if not careful
    path('workers/', include('workers.urls')),
    path('employers/', include('employers.urls')),
    path('jobs/', include('jobs.urls')),
    path('sms/', include('sms_simulator.urls')),
    path('notifications/', include('notifications.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)