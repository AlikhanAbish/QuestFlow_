"""
Notification views — TZ sections 4.8, 6.6.

HTMX-first: all views check request.htmx and return partials when appropriate.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.generic import ListView, View

from apps.core.mixins import HtmxTemplateResponseMixin
from .models import NotificationScope
from .services import NotificationService

FILTER_TABS = (
    ('all', 'All'),
    ('unread', 'Unread'),
    ('tasks', 'Tasks'),
    ('gamification', 'Gamification'),
    ('burnout', 'Burnout'),
)


def _list_context(request, **extra):
    user = request.user
    filter_key = request.GET.get('filter', 'all')
    scope = request.GET.get('scope') or None
    if scope == 'all':
        scope = None

    ctx = {
        'notifications': NotificationService.get_for_user(
            user,
            filter_key=filter_key,
            scope=scope,
        ),
        'unread_count': NotificationService.get_unread_count(user),
        'active_filter': filter_key,
        'active_scope': scope or 'all',
        'is_manager_or_admin': NotificationService.is_manager_or_admin(user),
        'personal_unread': NotificationService.get_unread_count(
            user, scope=NotificationScope.PERSONAL,
        ),
        'team_unread': NotificationService.get_unread_count(
            user, scope=NotificationScope.TEAM,
        ) if NotificationService.is_manager_or_admin(user) else 0,
        'notif_context': 'list',
        'filter_tabs': FILTER_TABS,
        'refresh_header': False,
    }
    ctx.update(extra)
    return ctx


def _dropdown_response(request):
    notifications = NotificationService.get_recent(request.user, limit=8)
    unread_count = NotificationService.get_unread_count(request.user)
    return TemplateResponse(request, 'notifications/partials/_bell_dropdown.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'notif_context': 'dropdown',
    })


class NotificationsListView(LoginRequiredMixin, HtmxTemplateResponseMixin, ListView):
    """
    TZ 4.8: Full-page notification history with HTMX partial support.
    GET /notifications/ → full page
    GET /notifications/ (htmx) → partial list only
    """
    template_name = 'notifications/list.html'
    htmx_template_name = 'notifications/partials/_list_partial.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        filter_key = self.request.GET.get('filter', 'all')
        scope = self.request.GET.get('scope') or None
        if scope == 'all':
            scope = None
        return NotificationService.get_for_user(
            self.request.user,
            filter_key=filter_key,
            scope=scope,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filter_key = self.request.GET.get('filter', 'all')
        scope = self.request.GET.get('scope') or None
        if scope == 'all':
            scope = None

        ctx['unread_count'] = NotificationService.get_unread_count(user)
        ctx['active_filter'] = filter_key
        ctx['active_scope'] = scope or 'all'
        ctx['is_manager_or_admin'] = NotificationService.is_manager_or_admin(user)
        ctx['personal_unread'] = NotificationService.get_unread_count(
            user, scope=NotificationScope.PERSONAL,
        )
        ctx['team_unread'] = (
            NotificationService.get_unread_count(user, scope=NotificationScope.TEAM)
            if ctx['is_manager_or_admin'] else 0
        )
        ctx['notif_context'] = 'list'
        ctx['filter_tabs'] = FILTER_TABS
        ctx['refresh_header'] = False
        return ctx


def _list_response(request, *, refresh_header: bool = False):
    ctx = _list_context(request)
    paginator = Paginator(ctx['notifications'], NotificationsListView.paginate_by)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    ctx['notifications'] = page_obj.object_list
    ctx['page_obj'] = page_obj
    ctx['is_paginated'] = page_obj.has_other_pages()
    ctx['refresh_header'] = refresh_header
    return TemplateResponse(request, 'notifications/partials/_list_partial.html', ctx)


class NotificationsPartialView(LoginRequiredMixin, View):
    """
    TZ 6.6: Returns the bell-dropdown partial with the latest N notifications.
    Used by HTMX hx-get on the bell icon — polled every 60 s for live updates.
    GET /notifications/partial/
    """
    def get(self, request, *args, **kwargs):
        return _dropdown_response(request)


class MarkNotificationReadView(LoginRequiredMixin, View):
    """
    TZ 5.7: Mark a single notification as read via HTMX POST.
    Response target depends on HX-Target (list item, list, or bell dropdown).
    POST /notifications/<pk>/read/
    """
    def post(self, request, pk, *args, **kwargs):
        NotificationService.mark_as_read(pk, request.user)
        hx_target = request.headers.get('HX-Target', '').lstrip('#')

        if hx_target.startswith('notif-') and hx_target != 'notif-dropdown-content':
            notif = NotificationService.get_notification_for_user(request.user, pk)
            if notif:
                return TemplateResponse(
                    request,
                    'notifications/partials/_notification_item.html',
                    {'notif': notif, 'notif_context': 'list'},
                )
            return HttpResponse('')

        if hx_target == 'notif-list':
            return _list_response(request, refresh_header=True)

        return _dropdown_response(request)


class MarkAllReadView(LoginRequiredMixin, View):
    """
    Mark notifications as read via HTMX POST.
    POST /notifications/read-all/
    """
    def post(self, request, *args, **kwargs):
        scope = request.POST.get('scope') or request.GET.get('scope')
        if scope == 'all':
            scope = None
        NotificationService.mark_all_as_read(request.user, scope=scope)

        hx_target = request.headers.get('HX-Target', '').lstrip('#')
        if hx_target == 'notif-list':
            return _list_response(request, refresh_header=True)

        return _dropdown_response(request)
