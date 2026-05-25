from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # Companies
    path('companies/', views.AdminCompanyListView.as_view(), name='company-list'),
    path('companies/create/', views.AdminCompanyCreateView.as_view(), name='company-create'),
    path('companies/<int:pk>/', views.AdminCompanyDetailView.as_view(), name='company-detail'),
    path('companies/<int:pk>/deactivate/', views.AdminCompanyDeactivateView.as_view(), name='company-deactivate'),
    
    # Users
    path('users/', views.AdminUserListView.as_view(), name='user-list'),
    path('users/<int:pk>/role/', views.AdminUserRoleView.as_view(), name='user-role'),
    path('users/<int:pk>/deactivate/', views.AdminUserDeactivateView.as_view(), name='user-deactivate'),
    
    # Gamification
    path('gamification/', views.AdminGamificationSettingsView.as_view(), name='gamification-settings'),
    path('gamification/rules/', views.AdminGamificationRulesUpdateView.as_view(), name='gamification-rules-update'),
    path('gamification/badges/', views.AdminBadgeListView.as_view(), name='gamification-badges'),
    path('gamification/badges/create/', views.AdminBadgeCreateView.as_view(), name='gamification-badge-create'),
    
    # Logs & Settings
    path('audit-log/', views.AdminAuditLogView.as_view(), name='audit-log'),
    path('settings/', views.AdminSystemSettingsView.as_view(), name='system-settings'),
]
