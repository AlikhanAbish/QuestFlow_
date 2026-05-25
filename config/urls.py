from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.companies.urls', namespace='companies')),
    path('tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('gamification/', include('apps.gamification.urls', namespace='gamification')),
    path('burnout/', include('apps.burnout.urls', namespace='burnout')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    # Telegram Bot: /telegram/webhook/ and /telegram/connect/
    path('telegram/', include('apps.telegram_bot.urls', namespace='telegram_bot')),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),
]


# Serve media/static in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
