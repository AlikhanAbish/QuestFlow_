from django.urls import path
from . import views

app_name = 'burnout'

urlpatterns = [
    path('assessment/', views.BurnoutAssessmentView.as_view(), name='assessment'),
    path('assessment/submit/', views.BurnoutAssessmentSubmitView.as_view(), name='assessment_submit'),
    path('history/', views.BurnoutHistoryView.as_view(), name='history'),
    path('team-summary/', views.TeamBurnoutSummaryView.as_view(), name='team_summary'),
]
