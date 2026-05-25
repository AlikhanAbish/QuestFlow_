from celery import shared_task
from django.utils import timezone
from apps.gamification.models import Streak, UserLevel


@shared_task(name="apps.gamification.tasks.check_streak_breaks")
def check_streak_breaks():
    """
    TZ 6.6: Reset current streak to 0 for users who haven't been active
    for more than 1 day. Runs daily at 00:05.
    """
    today = timezone.now().date()
    # Users whose last_active was before yesterday
    inactive_streaks = Streak.objects.filter(
        last_active__lt=today - timezone.timedelta(days=1),
        current__gt=0
    )

    count = inactive_streaks.update(current=0)
    return f"Reset streaks for {count} inactive users."


@shared_task(name="apps.gamification.tasks.reset_weekly_xp")
def reset_weekly_xp():
    """
    TZ 6.6: Reset weekly_xp to 0 for all users every Monday at 00:01.
    Used for the weekly leaderboard / XP-counter weekly progress display.
    """
    count = UserLevel.objects.filter(weekly_xp__gt=0).update(weekly_xp=0)
    return f"Reset weekly XP for {count} users."
