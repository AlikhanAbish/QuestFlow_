"""
Celery tasks for Telegram bot — TZ 6.6.

Tasks:
  send_daily_reminders        — daily 09:00 UTC
  send_assessment_reminders   — Friday 17:00 UTC
  send_burnout_alerts         — triggered after BurnoutScore calculation
"""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _send(telegram_id: int, text: str) -> None:
    """Fire-and-forget send using TelegramService synchronous path."""
    from .services import TelegramService
    TelegramService.send_message(telegram_id, text)


# ---------------------------------------------------------------------------
# send_daily_reminders — schedule: daily 09:00 UTC
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_daily_reminders", queue="telegram")
def send_daily_reminders(self: Any) -> dict:
    """
    TZ 6.6: Send morning reminders to all active TelegramUsers.
    Reminds users to log in, check tasks, and keep their streak alive.
    """
    from .models import TelegramUser

    users = TelegramUser.objects.filter(is_active=True, telegram_id__gt=0).select_related(
        "user__level_data", "user__streak"
    )
    sent = 0
    failed = 0

    for tg_user in users:
        user = tg_user.user
        if not user.is_active:
            continue

        try:
            streak = user.streak.current
        except Exception:
            streak = 0

        try:
            level = user.level_data.level
        except Exception:
            level = 1

        streak_msg = f"🔥 Keep your {streak}-day streak going!" if streak > 1 else "🔥 Start your streak today!"
        text = (
            f"☀️ <b>Good morning, {user.first_name or 'teammate'}!</b>\n\n"
            f"Your QuestFlow day awaits:\n"
            f"• Level <b>{level}</b> hero, ready for action?\n"
            f"{streak_msg}\n\n"
            f"👉 <a href='http://questflow.app/dashboard/'>Open Dashboard</a>"
        )
        from .services import TelegramService
        ok = TelegramService.send_message(tg_user.telegram_id, text)
        if ok:
            sent += 1
        else:
            failed += 1

    logger.info("send_daily_reminders: sent=%d failed=%d", sent, failed)
    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# send_assessment_reminders — schedule: Friday 17:00 UTC
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_assessment_reminders", queue="telegram")
def send_assessment_reminders(self: Any) -> dict:
    """
    TZ 2.1.4: Remind users to complete their weekly self-assessment
    if they haven't done it by Friday 17:00.
    """
    from .models import TelegramUser
    from apps.burnout.models import AssessmentForm

    now = timezone.now()
    current_week = now.isocalendar()[1]
    current_year = now.year

    # Find active TelegramUsers who haven't submitted this week's assessment
    completed_user_ids = set(
        AssessmentForm.objects.filter(
            week_number=current_week, year=current_year
        ).values_list("user_id", flat=True)
    )

    pending = TelegramUser.objects.filter(
        is_active=True, telegram_id__gt=0
    ).exclude(user_id__in=completed_user_ids).select_related("user")

    sent = 0
    for tg_user in pending:
        if not tg_user.user.is_active:
            continue
        text = (
            "📝 <b>Weekly Self-Assessment Reminder</b>\n\n"
            "You haven't completed this week's burnout check yet!\n\n"
            "It takes less than 2 minutes and helps track your wellbeing.\n\n"
            "👉 <a href='http://questflow.app/burnout/assessment/'>Complete Assessment</a>"
        )
        from .services import TelegramService
        if TelegramService.send_message(tg_user.telegram_id, text):
            sent += 1

    logger.info("send_assessment_reminders: sent=%d (week %d/%d)", sent, current_week, current_year)
    return {"sent": sent, "week": current_week, "year": current_year}


# ---------------------------------------------------------------------------
# send_burnout_alerts — triggered on BurnoutScore change
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_burnout_alerts", queue="telegram")
def send_burnout_alerts(self: Any, user_id: int, old_level: str, new_level: str) -> dict:
    """
    TZ 2.1.5 / 6.6: Alert the user when their Burnout Score changes.
    Only sent if the user has an active Telegram account.
    """
    from .models import TelegramUser

    try:
        tg_user = TelegramUser.objects.get(user_id=user_id, is_active=True, telegram_id__gt=0)
    except TelegramUser.DoesNotExist:
        logger.debug("send_burnout_alerts: no active TelegramUser for user_id=%s", user_id)
        return {"sent": False, "reason": "no_telegram_user"}

    level_emojis = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    level_labels = {"green": "Healthy", "yellow": "At Risk", "red": "Burned Out"}

    old_emoji = level_emojis.get(old_level, "❓")
    new_emoji = level_emojis.get(new_level, "❓")
    old_label = level_labels.get(old_level, old_level)
    new_label = level_labels.get(new_level, new_level)

    if new_level == "red":
        advice = "⚠️ Consider talking to your manager or HR about workload."
    elif new_level == "yellow":
        advice = "💡 Keep an eye on your workload — take short breaks."
    else:
        advice = "🎉 Great job keeping yourself healthy!"

    text = (
        f"📊 <b>Burnout Score Updated</b>\n\n"
        f"Your status changed:\n"
        f"{old_emoji} {old_label} → {new_emoji} <b>{new_label}</b>\n\n"
        f"{advice}\n\n"
        f"👉 <a href='http://questflow.app/burnout/history/'>View History</a>"
    )

    from .services import TelegramService
    ok = TelegramService.send_message(tg_user.telegram_id, text)
    logger.info(
        "send_burnout_alerts: user_id=%s %s→%s sent=%s",
        user_id, old_level, new_level, ok,
    )
    return {"sent": ok, "user_id": user_id, "old": old_level, "new": new_level}
