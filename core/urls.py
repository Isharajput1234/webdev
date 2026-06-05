from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('', include(('apps.jobs.urls', 'jobs'), namespace='jobs')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)