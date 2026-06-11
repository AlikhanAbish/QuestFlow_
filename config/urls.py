from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Простой редирект для главной страницы
def home_redirect(request):
    if request.user.is_authenticated:
        if request.user.role in ['manager', 'admin']:
            return redirect('accounts:dashboard-manager')
        else:
            return redirect('accounts:dashboard-employee')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),

    # Главная страница
    path('', home_redirect, name='home'),

    # Accounts (логин, дашборды, профиль)
    path('', include('apps.accounts.urls', namespace='accounts')),

    # Остальные приложения
    path('tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('companies/', include('apps.companies.urls', namespace='companies')),
    path('gamification/', include('apps.gamification.urls', namespace='gamification')),
    path('burnout/', include('apps.burnout.urls', namespace='burnout')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('telegram/', include('apps.telegram_bot.urls', namespace='telegram_bot')),
]

# Serve media/static in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
