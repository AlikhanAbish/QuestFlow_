"""
Analytics Service — TZ 2.2.3 / 4.7
All business logic for the analytics dashboard.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone

from apps.burnout.models import AssessmentForm, BurnoutLevel
from apps.gamification.models import XPTransaction
from apps.tasks.models import Task, TaskStatus


class AnalyticsService:
    """
    Provides aggregated analytics metrics for a Manager's team.
    All methods are company-isolated via the team parameter.
    """

    # ------------------------------------------------------------------ #
    # Task Completion Metrics
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_tasks_completion_metrics(team, days: int = 30) -> dict:
        """
        Returns % of tasks completed on time vs overdue for the last `days` days.
        Returns a dict suitable for Chart.js consumption.
        """
        since = timezone.now() - timedelta(days=days)
        tasks_qs = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            completed_at__gte=since,
        )
        total_completed = tasks_qs.count()

        on_time = tasks_qs.filter(
            status=TaskStatus.DONE,
            completed_at__isnull=False,
            deadline__isnull=False,
            completed_at__lte=models_deadline_field_ref(),  # see helper
        ).count()

        # Simpler approach: completed before or on deadline
        on_time = tasks_qs.filter(
            status=TaskStatus.DONE,
            completed_at__isnull=False,
        ).extra(
            where=["completed_at <= deadline OR deadline IS NULL"]
        ).count()

        overdue = total_completed - on_time

        # Also count currently overdue (not yet done)
        currently_overdue = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            status=TaskStatus.OVERDUE,
        ).count()

        pct_on_time = round((on_time / total_completed * 100), 1) if total_completed else 0
        pct_overdue = round(100 - pct_on_time, 1) if total_completed else 0

        return {
            "on_time": on_time,
            "overdue": overdue,
            "total_completed": total_completed,
            "currently_overdue": currently_overdue,
            "pct_on_time": pct_on_time,
            "pct_overdue": pct_overdue,
        }

    @staticmethod
    def get_tasks_daily_stats(team, days: int = 30) -> dict:
        """
        Returns daily completed task counts for bar chart.
        {"labels": [...], "data": [...]}
        """
        since = timezone.now().date() - timedelta(days=days)
        labels = []
        data = []

        for i in range(days):
            day = since + timedelta(days=i)
            count = Task.objects.filter(
                assigned_to__team=team,
                is_deleted=False,
                status=TaskStatus.DONE,
                completed_at__date=day,
            ).count()
            labels.append(day.strftime("%d %b"))
            data.append(count)

        return {"labels": labels, "data": data}

    # ------------------------------------------------------------------ #
    # XP Dynamics
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_team_xp_dynamics(team, days: int = 30) -> dict:
        """
        Daily XP earned by the entire team over the last `days` days.
        Returns {"labels": [...], "data": [...]}
        """
        since = timezone.now().date() - timedelta(days=days)
        team_user_ids = list(
            team.user_set.values_list("id", flat=True)
        )

        labels = []
        data = []
        for i in range(days):
            day = since + timedelta(days=i)
            total_xp = (
                XPTransaction.objects.filter(
                    user_id__in=team_user_ids,
                    created_at__date=day,
                    amount__gt=0,
                ).aggregate(s=Sum("amount"))["s"]
                or 0
            )
            labels.append(day.strftime("%d %b"))
            data.append(total_xp)

        return {"labels": labels, "data": data}

    @staticmethod
    def get_team_total_xp(team) -> int:
        """Sum of all XP earned by team members (total_xp from UserLevel)."""
        from apps.gamification.models import UserLevel
        result = UserLevel.objects.filter(
            user__team=team
        ).aggregate(s=Sum("total_xp"))
        return result["s"] or 0

    # ------------------------------------------------------------------ #
    # Burnout Trend
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_burnout_trend(team, weeks: int = 8) -> dict:
        """
        Weekly count of Green, Yellow, Red statuses for consenting team members.
        Returns {"labels": [...], "green": [...], "yellow": [...], "red": [...]}
        """
        from apps.burnout.calculator import MBICalculator
        today = date.today()
        # Start from `weeks` ISO weeks ago
        start_date = today - timedelta(weeks=weeks)

        consenting_ids = list(
            team.user_set.filter(
                burnout_score__manager_consent=True
            ).values_list("id", flat=True)
        )

        labels = []
        green_data = []
        yellow_data = []
        red_data = []
        
        calculator = MBICalculator()

        for i in range(weeks):
            ref_date = start_date + timedelta(weeks=i)
            iso = ref_date.isocalendar()
            yr, wk = iso[0], iso[1]

            forms = AssessmentForm.objects.filter(
                user_id__in=consenting_ids,
                year=yr,
                week_number=wk,
            )
            
            counts = {BurnoutLevel.GREEN: 0, BurnoutLevel.YELLOW: 0, BurnoutLevel.RED: 0}
            for form in forms:
                level = calculator.calculate(form)
                counts[level] += 1

            labels.append(f"W{wk}")
            green_data.append(counts[BurnoutLevel.GREEN])
            yellow_data.append(counts[BurnoutLevel.YELLOW])
            red_data.append(counts[BurnoutLevel.RED])

        return {
            "labels": labels,
            "green": green_data,
            "yellow": yellow_data,
            "red": red_data,
        }

    @staticmethod
    def get_burnout_distribution(team) -> dict:
        """
        Current distribution of burnout scores for consenting team members.
        {"green": n, "yellow": n, "red": n}
        """
        from apps.burnout.models import BurnoutScore
        qs = BurnoutScore.objects.filter(
            user__team=team,
            manager_consent=True,
        )
        dist = {level: 0 for level in BurnoutLevel.values}
        for row in qs.values("score").annotate(c=Count("id")):
            dist[row["score"]] = row["c"]
        return dist

    # ------------------------------------------------------------------ #
    # Employee Activity Ranking
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_employee_activity_ranking(team, top_n: int = 5) -> dict:
        """
        Returns top-N most active and top-N least active team members,
        ranked by total_xp from UserLevel.
        """
        from apps.gamification.models import UserLevel

        members_qs = (
            UserLevel.objects.filter(user__team=team)
            .select_related("user", "user__streak")
            .order_by("-total_xp")
        )

        all_members = list(members_qs)
        top_active = all_members[:top_n]
        least_active = list(reversed(all_members[-top_n:])) if len(all_members) > top_n else []

        return {
            "top_active": top_active,
            "least_active": least_active,
        }

    # ------------------------------------------------------------------ #
    # Summary Card Metrics
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_summary_stats(team) -> dict:
        """
        Quick summary KPIs for the top of the analytics dashboard.
        """
        total_members = team.user_set.count()
        active_tasks = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
        ).count()
        done_tasks = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            status=TaskStatus.DONE,
        ).count()
        overdue_tasks = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            status=TaskStatus.OVERDUE,
        ).count()

        from apps.gamification.models import UserLevel
        total_xp = (
            UserLevel.objects.filter(user__team=team)
            .aggregate(s=Sum("total_xp"))["s"] or 0
        )

        return {
            "total_members": total_members,
            "active_tasks": active_tasks,
            "done_tasks": done_tasks,
            "overdue_tasks": overdue_tasks,
            "total_xp": total_xp,
        }

    # ------------------------------------------------------------------ #
    # Task Metrics & Engagement Rating (Requested)
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_task_metrics(team, days: int = 30) -> dict:
        """
        Returns % of tasks completed on time in the last `days` days
        and the average task completion time.
        """
        since = timezone.now() - timedelta(days=days)
        tasks_qs = Task.objects.filter(
            assigned_to__team=team,
            is_deleted=False,
            completed_at__gte=since,
            status=TaskStatus.DONE,
        )
        total_completed = tasks_qs.count()

        # On-time: completed_at <= deadline OR deadline is null
        on_time = tasks_qs.filter(
            Q(completed_at__lte=F('deadline')) | Q(deadline__isnull=True)
        ).count()

        pct_on_time = round((on_time / total_completed * 100), 1) if total_completed else 0

        avg_completion_time = None
        if total_completed > 0:
            duration_expr = ExpressionWrapper(
                F('completed_at') - F('created_at'),
                output_field=DurationField()
            )
            avg_td = tasks_qs.annotate(duration=duration_expr).aggregate(avg_time=Avg('duration'))['avg_time']
            if avg_td:
                # Format as string to drop microseconds (e.g., '1 day, 2:30:00')
                avg_completion_time = str(avg_td).split('.')[0]

        return {
            "pct_on_time": pct_on_time,
            "avg_completion_time": avg_completion_time,
        }

    @staticmethod
    def get_engagement_rating(team, top_n: int = 5) -> dict:
        """
        Returns the most active and least active users in the team,
        using XP (total_xp from UserLevel) as the activity metric.
        """
        from apps.gamification.models import UserLevel

        members_qs = (
            UserLevel.objects.filter(user__team=team, user__is_active=True)
            .select_related("user")
            .order_by("-total_xp")
        )

        all_members = list(members_qs)
        top_active = all_members[:top_n]
        least_active = list(reversed(all_members[-top_n:])) if len(all_members) > 0 else []

        return {
            "most_active": top_active,
            "least_active": least_active,
        }
