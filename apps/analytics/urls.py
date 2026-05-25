from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("team/", views.TeamAnalyticsView.as_view(), name="team_dashboard"),
    path("team/tasks-chart/", views.TasksChartPartialView.as_view(), name="tasks-chart"),
    path("team/xp-chart/", views.XPChartPartialView.as_view(), name="xp-chart"),
    path("team/burnout-trend/", views.BurnoutTrendPartialView.as_view(), name="burnout-trend"),
    path("team/activity-ranking/", views.ActivityRankingPartialView.as_view(), name="activity-ranking"),
]
