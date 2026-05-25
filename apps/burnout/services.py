from django.utils import timezone
from django.db.models import F
from apps.tasks.models import Task, TaskStatus
from apps.burnout.models import AssessmentForm, BurnoutScore
from apps.burnout.calculator import MBICalculator
from statistics import mean
import datetime

class BurnoutService:
    def __init__(self, user):
        self.user = user
        self.calculator = MBICalculator()

    def get_tasks_completion_rate(self) -> float:
        """Calculate completion rate for the current week."""
        now = timezone.now()
        # Start of current week (Monday)
        week_start = now - datetime.timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        # End of current week (Next Monday)
        week_end = week_start + datetime.timedelta(days=7)

        tasks_due = Task.objects.filter(
            assigned_to=self.user,
            deadline__gte=week_start,
            deadline__lt=week_end,
            is_deleted=False
        )
        total = tasks_due.count()
        if total == 0:
            return 1.0
            
        completed_on_time = tasks_due.filter(
            status=TaskStatus.DONE,
            completed_at__lte=F('deadline')
        ).count()
        
        return completed_on_time / total

    def process_assessment(self, form_data: dict) -> BurnoutScore:
        now = timezone.now()
        iso_year, iso_week, _ = now.isocalendar()
        
        completion_rate = self.get_tasks_completion_rate()
        
        # Check if form already exists to avoid unique constraint error
        assessment, created = AssessmentForm.objects.update_or_create(
            user=self.user,
            week_number=iso_week,
            year=iso_year,
            defaults={
                'ex1': form_data['ex1'],
                'ex2': form_data['ex2'],
                'ex3': form_data['ex3'],
                'cy1': form_data['cy1'],
                'cy2': form_data['cy2'],
                'cy3': form_data['cy3'],
                'ef1': form_data['ef1'],
                'ef2': form_data['ef2'],
                'ef3': form_data['ef3'],
                'tasks_completion_rate': completion_rate
            }
        )
        
        burnout_level = self.calculator.calculate(assessment)
        
        # Track old score for alerts
        old_level = 'green' # Default
        try:
            old_score_obj = BurnoutScore.objects.get(user=self.user)
            old_level = old_score_obj.score
        except BurnoutScore.DoesNotExist:
            pass
        
        score, _ = BurnoutScore.objects.update_or_create(
            user=self.user,
            defaults={
                'score': burnout_level,
                'exhaustion_avg': mean([assessment.ex1, assessment.ex2, assessment.ex3]),
                'cynicism_avg': mean([assessment.cy1, assessment.cy2, assessment.cy3]),
                'efficacy_avg': mean([assessment.ef1, assessment.ef2, assessment.ef3]),
            }
        )
        
        # Trigger in-app notification if status changed
        if old_level != burnout_level:
            from apps.notifications.services import NotificationService
            NotificationService.notify_burnout_alert(self.user, burnout_level)
            
        # Trigger Telegram alert if status changed
        if old_level != burnout_level:
            from apps.telegram_bot.tasks import send_burnout_alerts
            send_burnout_alerts.delay(self.user.id, old_level, burnout_level)
            
        return score

    def set_manager_consent(self, consent: bool):
        score, created = BurnoutScore.objects.get_or_create(user=self.user)
        score.manager_consent = consent
        score.save()

    @staticmethod
    def get_team_summary(team):
        """Get team burnout summary: only active members who gave manager_consent."""
        scores = BurnoutScore.objects.filter(
            user__team=team,
            user__is_active=True,
            user__company=team.company,
            manager_consent=True
        ).values_list('score', flat=True)
        
        scores_list = list(scores)
        total = len(scores_list)
        
        if total == 0:
            return {'green': 0, 'yellow': 0, 'red': 0, 'total': 0}
            
        return {
            'green': scores_list.count('green'),
            'yellow': scores_list.count('yellow'),
            'red': scores_list.count('red'),
            'total': total
        }
