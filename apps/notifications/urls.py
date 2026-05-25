from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Full list page
    path('', views.NotificationsListView.as_view(), name='list'),

    # Bell dropdown partial (polled by HTMX)
    path('partial/', views.NotificationsPartialView.as_view(), name='partial'),

    # Mark single notification read
    path('<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='mark-read'),

    # Mark all read
    path('read-all/', views.MarkAllReadView.as_view(), name='mark-all-read'),
]
