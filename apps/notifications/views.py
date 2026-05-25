"""
Notification views — TZ sections 4.8, 6.6.

HTMX-first: all views check request.htmx and return partials when appropriate.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.generic import ListView, View

from apps.core.mixins import HtmxTemplateResponseMixin
from .models import Notification
from .services import NotificationService


class NotificationsListView(LoginRequiredMixin, HtmxTemplateResponseMixin, ListView):
    """
    TZ 4.8: Full-page notification history with HTMX partial support.
    GET /notifications/ → full page
    GET /notifications/ (htmx) → partial list only
    """
    template_name      = 'notifications/list.html'
    htmx_template_name = 'notifications/partials/_list_partial.html'
    context_object_name = 'notifications'
    paginate_by        = 20

    def get_queryset(self):
        return NotificationService.get_all_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unread_count'] = NotificationService.get_unread_count(self.request.user)
        return ctx


class NotificationsPartialView(LoginRequiredMixin, View):
    """
    TZ 6.6: Returns the bell-dropdown partial with the latest N notifications.
    Used by HTMX hx-get on the bell icon — polled every 60 s for live updates.
    GET /notifications/partial/
    """
    def get(self, request, *args, **kwargs):
        notifications = NotificationService.get_recent(request.user, limit=8)
        unread_count  = NotificationService.get_unread_count(request.user)
        return TemplateResponse(request, 'notifications/partials/_bell_dropdown.html', {
            'notifications': notifications,
            'unread_count':  unread_count,
        })


class MarkNotificationReadView(LoginRequiredMixin, View):
    """
    TZ 5.7: Mark a single notification as read via HTMX POST.
    Returns the updated bell-dropdown so HTMX can swap it in place.
    POST /notifications/<pk>/read/
    """
    def post(self, request, pk, *args, **kwargs):
        NotificationService.mark_as_read(pk, request.user)
        # Re-render the dropdown so the counter & item styling update live
        notifications = NotificationService.get_recent(request.user, limit=8)
        unread_count  = NotificationService.get_unread_count(request.user)
        return TemplateResponse(request, 'notifications/partials/_bell_dropdown.html', {
            'notifications': notifications,
            'unread_count':  unread_count,
        })


class MarkAllReadView(LoginRequiredMixin, View):
    """
    Mark all notifications as read via HTMX POST.
    POST /notifications/read-all/
    """
    def post(self, request, *args, **kwargs):
        NotificationService.mark_all_as_read(request.user)
        notifications = NotificationService.get_recent(request.user, limit=8)
        return TemplateResponse(request, 'notifications/partials/_bell_dropdown.html', {
            'notifications': notifications,
            'unread_count':  0,
        })
