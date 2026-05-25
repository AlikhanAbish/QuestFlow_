"""
Analytics Views — TZ 2.2.3 / 4.7
TeamAnalyticsView + HTMX chart partials.
"""
import json

from django.views.generic import TemplateView
from django.template.response import TemplateResponse

from apps.accounts.mixins import RoleRequiredMixin
from apps.accounts.models import Role
from .services import AnalyticsService


def _get_team(request):
    """Return the team of the current user, or None."""
    return getattr(request.user, "team", None)


class TeamAnalyticsView(RoleRequiredMixin, TemplateView):
    """
    Main analytics dashboard page for Managers / Admins.
    Charts are loaded lazily via HTMX (hx-trigger="load").
    """
    template_name = "analytics/team_dashboard.html"
    required_roles = [Role.MANAGER, Role.ADMIN]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = _get_team(self.request)
        if team:
            ctx["team"] = team
            ctx["summary"] = AnalyticsService.get_summary_stats(team)
            ctx["task_metrics"] = AnalyticsService.get_task_metrics(team)
            ctx["engagement_rating"] = AnalyticsService.get_engagement_rating(team)
        else:
            ctx["team"] = None
            ctx["summary"] = {
                "total_members": 0,
                "active_tasks": 0,
                "done_tasks": 0,
                "overdue_tasks": 0,
                "total_xp": 0,
            }
            ctx["task_metrics"] = {"pct_on_time": 0, "avg_completion_time": None}
            ctx["engagement_rating"] = {"most_active": [], "least_active": []}
        return ctx


class TasksChartPartialView(RoleRequiredMixin, TemplateView):
    """HTMX partial — % задач в срок за 30 дней (doughnut + bar)."""
    template_name = "analytics/partials/_tasks_chart.html"
    required_roles = [Role.MANAGER, Role.ADMIN]

    def get(self, request, *args, **kwargs):
        if not getattr(request, 'htmx', False):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest("HTMX request required")
        
        team = _get_team(request)
        ctx = {}
        if team:
            metrics = AnalyticsService.get_tasks_completion_metrics(team, days=30)
            daily = AnalyticsService.get_tasks_daily_stats(team, days=30)
            ctx = {
                "metrics": metrics,
                "daily_labels_json": json.dumps(daily["labels"]),
                "daily_data_json": json.dumps(daily["data"]),
                "on_time_pct": metrics["pct_on_time"],
                "overdue_pct": metrics["pct_overdue"],
            }
        return TemplateResponse(request, self.template_name, ctx)


class XPChartPartialView(RoleRequiredMixin, TemplateView):
    """HTMX partial — динамика XP команды за 30 дней."""
    template_name = "analytics/partials/_xp_chart.html"
    required_roles = [Role.MANAGER, Role.ADMIN]

    def get(self, request, *args, **kwargs):
        if not getattr(request, 'htmx', False):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest("HTMX request required")

        team = _get_team(request)
        ctx = {}
        if team:
            dynamics = AnalyticsService.get_team_xp_dynamics(team, days=30)
            ctx = {
                "labels_json": json.dumps(dynamics["labels"]),
                "data_json": json.dumps(dynamics["data"]),
                "total_xp": sum(v for v in dynamics["data"] if v),
            }
        return TemplateResponse(request, self.template_name, ctx)


class BurnoutTrendPartialView(RoleRequiredMixin, TemplateView):
    """HTMX partial — burnout trend по неделям."""
    template_name = "analytics/partials/_burnout_trend_chart.html"
    required_roles = [Role.MANAGER, Role.ADMIN]

    def get(self, request, *args, **kwargs):
        if not getattr(request, 'htmx', False):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest("HTMX request required")

        team = _get_team(request)
        ctx = {}
        if team:
            trend = AnalyticsService.get_burnout_trend(team, weeks=8)
            distribution = AnalyticsService.get_burnout_distribution(team)
            ctx = {
                "labels_json": json.dumps(trend["labels"]),
                "green_json": json.dumps(trend["green"]),
                "yellow_json": json.dumps(trend["yellow"]),
                "red_json": json.dumps(trend["red"]),
                "distribution": distribution,
                "dist_total": sum(distribution.values()),
            }
        return TemplateResponse(request, self.template_name, ctx)


class ActivityRankingPartialView(RoleRequiredMixin, TemplateView):
    """HTMX partial — топ и наименее активные сотрудники."""
    template_name = "analytics/partials/_activity_ranking.html"
    required_roles = [Role.MANAGER, Role.ADMIN]

    def get(self, request, *args, **kwargs):
        team = _get_team(request)
        ctx = {}
        if team:
            ctx["ranking"] = AnalyticsService.get_employee_activity_ranking(team, top_n=5)
        return TemplateResponse(request, self.template_name, ctx)
