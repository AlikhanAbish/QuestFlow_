"""
Celery tasks for Telegram bot — TZ 6.6.

Tasks:
  send_daily_reminders              — daily 09:00 UTC
  send_assessment_reminders         — Friday 17:00 UTC
  send_burnout_alerts               — employee personal burnout change
  send_level_up_notification        — employee level up
  send_badge_notification           — employee badge earned
  send_new_task_notification        — employee new task assigned
  send_milestone_notification       — manager/admin employee milestone
  send_task_completed_notification  — manager/admin employee task done
  send_team_burnout_notification    — manager/admin team burnout change
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
    TZ 2.1.5 / 6.6: Alert the employee when their Burnout Score changes.
    """
    from django.contrib.auth import get_user_model

    from .notifications import format_burnout_level, send_to_user, web_url

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return {"sent": False, "reason": "user_not_found"}

    if new_level == "red":
        advice = "⚠️ Consider talking to your manager or HR about workload."
    elif new_level == "yellow":
        advice = "💡 Keep an eye on your workload — take short breaks."
    else:
        advice = "🎉 Great job keeping yourself healthy!"

    text = (
        f"📊 <b>Burnout Score Updated</b>\n\n"
        f"Your status changed:\n"
        f"{format_burnout_level(old_level)} → <b>{format_burnout_level(new_level)}</b>\n\n"
        f"{advice}"
    )

    buttons = [
        [
            {"text": "📈 History", "url": web_url("burnout:history")},
            {"text": "📝 Assessment", "url": web_url("burnout:assessment")},
        ],
    ]
    ok = send_to_user(user, text, button_rows=buttons)
    logger.info(
        "send_burnout_alerts: user_id=%s %s→%s sent=%s",
        user_id, old_level, new_level, ok,
    )
    return {"sent": ok, "user_id": user_id, "old": old_level, "new": new_level}


# ---------------------------------------------------------------------------
# send_level_up_notification — triggered on level up
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_level_up_notification", queue="telegram")
def send_level_up_notification(self: Any, user_id: int, new_level: int) -> dict:
    """
    TZ 2.1.3: Congratulate an employee on reaching a new level.
    Managers/admins are excluded — they get team alerts instead.
    """
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    from .models import TelegramUser
    from .services import TelegramService

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return {"sent": False, "reason": "user_not_found"}

    if user.role != Role.EMPLOYEE:
        return {"sent": False, "reason": "not_employee"}

    try:
        tg_user = TelegramUser.objects.get(user_id=user_id, is_active=True, telegram_id__gt=0)
    except TelegramUser.DoesNotExist:
        logger.debug("send_level_up_notification: no active TelegramUser for user_id=%s", user_id)
        return {"sent": False, "reason": "no_telegram_user"}

    milestone_emoji = "🎊" if new_level in {10, 20, 30, 40, 50} else "🎉"

    text = (
        f"{milestone_emoji} <b>Level Up!</b>\n\n"
        f"Congratulations! You've reached <b>Level {new_level}</b>!\n\n"
        f"Keep up the momentum and continue your amazing progress! 🚀\n\n"
        f"👉 <a href='http://questflow.app/dashboard/'>View your progress</a>"
    )

    ok = TelegramService.send_message(tg_user.telegram_id, text)
    logger.info("send_level_up_notification: user_id=%s level=%s sent=%s", user_id, new_level, ok)
    return {"sent": ok, "user_id": user_id, "level": new_level}


# ---------------------------------------------------------------------------
# send_badge_notification — triggered on badge earn
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_badge_notification", queue="telegram")
def send_badge_notification(self: Any, user_id: int, badge_id: int) -> dict:
    """
    TZ 2.1.3: Notify user when they earn a badge.
    Only sent if the user has an active Telegram account.
    """
    from .models import TelegramUser
    from .services import TelegramService
    from apps.gamification.models import Badge

    try:
        badge = Badge.objects.get(id=badge_id)
    except Badge.DoesNotExist:
        logger.warning("send_badge_notification: badge_id=%s not found", badge_id)
        return {"sent": False, "reason": "badge_not_found"}

    try:
        tg_user = TelegramUser.objects.get(user_id=user_id, is_active=True, telegram_id__gt=0)
    except TelegramUser.DoesNotExist:
        logger.debug("send_badge_notification: no active TelegramUser for user_id=%s", user_id)
        return {"sent": False, "reason": "no_telegram_user"}

    text = (
        f"🏅 <b>New Badge Unlocked!</b>\n\n"
        f"<b>{badge.name}</b>\n"
        f"<i>{badge.description}</i>\n\n"
        f"You're on fire! 🔥\n\n"
        f"👉 <a href='http://questflow.app/dashboard/'>View all badges</a>"
    )

    ok = TelegramService.send_message(tg_user.telegram_id, text)
    logger.info("send_badge_notification: user_id=%s badge_id=%s sent=%s", user_id, badge_id, ok)
    return {"sent": ok, "user_id": user_id, "badge_id": badge_id, "badge_name": badge.name}


# ---------------------------------------------------------------------------
# send_new_task_notification — triggered when task is created/assigned
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_new_task_notification", queue="telegram")
def send_new_task_notification(self: Any, user_id: int, task_id: int) -> dict:
    """
    Notify an employee when a new task is assigned to them.
    """
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    from apps.tasks.models import Task
    from .notifications import (
        PRIORITY_EMOJIS,
        format_deadline,
        send_to_user,
        web_url,
    )

    User = get_user_model()

    try:
        task = Task.objects.select_related("team", "assigned_to", "created_by").get(id=task_id)
    except Task.DoesNotExist:
        logger.warning("send_new_task_notification: task_id=%s not found", task_id)
        return {"sent": False, "reason": "task_not_found"}

    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return {"sent": False, "reason": "user_not_found"}

    if user.role != Role.EMPLOYEE:
        return {"sent": False, "reason": "not_employee"}

    priority_emoji = PRIORITY_EMOJIS.get(task.priority, "⚪")
    creator = ""
    if task.created_by:
        creator = f"\n👤 <b>Assigned by:</b> {task.created_by.get_full_name() or task.created_by.email}"

    team_text = f"\n👥 <b>Team:</b> {task.team.name}" if task.team else ""
    description = ""
    if task.description:
        description = f"\n\n<i>{task.description[:200]}</i>"

    text = (
        f"📝 <b>New Task Assigned</b>\n\n"
        f"{priority_emoji} <b>{task.title}</b>\n"
        f"📅 <b>Deadline:</b> {format_deadline(task.deadline)}"
        f"{team_text}{creator}"
        f"{description}"
    )

    buttons = [
        [
            {"text": "📋 View Task", "url": web_url("tasks:task_detail", task.pk)},
            {"text": "📂 All Tasks", "url": web_url("tasks:task_list")},
        ],
    ]
    ok = send_to_user(user, text, button_rows=buttons)
    if not ok:
        logger.warning(
            "send_new_task_notification: delivery failed user_id=%s task_id=%s "
            "(check Telegram link, TELEGRAM_BOT_TOKEN, and celery -Q telegram worker)",
            user_id,
            task_id,
        )
    logger.info("send_new_task_notification: user_id=%s task_id=%s sent=%s", user_id, task_id, ok)
    return {"sent": ok, "user_id": user_id, "task_id": task_id, "task_title": task.title}


# ---------------------------------------------------------------------------
# send_milestone_notification — manager/admin alert on employee milestone
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_milestone_notification", queue="telegram")
def send_milestone_notification(self: Any, employee_id: int, milestone_level: int) -> dict:
    """
    Notify managers/admins when an employee reaches a milestone level (10/20/30/40/50).
    """
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    from .notifications import (
        MILESTONE_LEVELS,
        get_employee_alert_recipients,
        send_to_recipients,
        web_url,
    )

    if milestone_level not in MILESTONE_LEVELS:
        return {"sent": 0, "reason": "not_milestone"}

    User = get_user_model()
    try:
        employee = User.objects.select_related("team", "company").get(
            pk=employee_id, is_active=True, role=Role.EMPLOYEE
        )
    except User.DoesNotExist:
        return {"sent": 0, "reason": "employee_not_found"}

    employee_name = employee.get_full_name() or employee.email
    team_name = employee.team.name if getattr(employee, "team", None) else "—"

    text = (
        f"🏆 <b>Milestone Achievement!</b>\n\n"
        f"<b>{employee_name}</b> reached <b>Level {milestone_level}</b>!\n"
        f"👥 Team: {team_name}\n\n"
        f"Consider granting a real-world reward to celebrate this milestone."
    )

    buttons = [
        [
            {"text": "👤 Employee Profile", "url": web_url("gamification:profile", employee.pk)},
            {"text": "📊 Dashboard", "url": web_url("accounts:dashboard-manager")},
        ],
    ]

    recipients = get_employee_alert_recipients(employee)
    sent = send_to_recipients(recipients, text, button_rows=buttons)
    logger.info(
        "send_milestone_notification: employee_id=%s level=%s sent=%s",
        employee_id, milestone_level, sent,
    )
    return {"sent": sent, "employee_id": employee_id, "milestone_level": milestone_level}


# ---------------------------------------------------------------------------
# send_task_completed_notification — manager/admin alert on task completion
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_task_completed_notification", queue="telegram")
def send_task_completed_notification(self: Any, task_id: int, completed_by_id: int) -> dict:
    """
    Notify managers/admins when an employee completes a task.
    """
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    from apps.tasks.models import Task
    from .notifications import (
        PRIORITY_EMOJIS,
        get_employee_alert_recipients,
        send_to_recipients,
        web_url,
    )

    User = get_user_model()

    try:
        task = Task.objects.select_related(
            "assigned_to", "assigned_to__team", "team"
        ).get(id=task_id)
    except Task.DoesNotExist:
        return {"sent": 0, "reason": "task_not_found"}

    assignee = task.assigned_to
    if not assignee or assignee.role != Role.EMPLOYEE:
        return {"sent": 0, "reason": "not_employee_task"}

    try:
        completed_by = User.objects.get(pk=completed_by_id)
    except User.DoesNotExist:
        completed_by = assignee

    assignee_name = assignee.get_full_name() or assignee.email
    priority_emoji = PRIORITY_EMOJIS.get(task.priority, "⚪")
    completed_at = task.completed_at.strftime("%b %d, %Y at %H:%M") if task.completed_at else "—"
    team_name = task.team.name if task.team else "—"

    text = (
        f"✅ <b>Task Completed</b>\n\n"
        f"<b>{assignee_name}</b> completed a task:\n"
        f"{priority_emoji} <b>{task.title}</b>\n"
        f"👥 Team: {team_name}\n"
        f"🕐 Completed: {completed_at}"
    )
    if completed_by.pk != assignee.pk:
        text += f"\n✔️ Marked done by: {completed_by.get_full_name() or completed_by.email}"

    buttons = [
        [
            {"text": "📋 View Task", "url": web_url("tasks:task_detail", task.pk)},
            {"text": "📂 Team Tasks", "url": web_url("tasks:task_list")},
        ],
    ]

    recipients = get_employee_alert_recipients(assignee)
    sent = send_to_recipients(recipients, text, button_rows=buttons)
    if not sent:
        logger.warning(
            "send_task_completed_notification: no delivery task_id=%s assignee_id=%s "
            "recipients=%s (link manager/admin Telegram or set team.manager)",
            task_id,
            assignee.pk,
            [r.email for r in recipients],
        )
    logger.info(
        "send_task_completed_notification: task_id=%s assignee_id=%s sent=%s",
        task_id, assignee.pk, sent,
    )
    return {"sent": sent, "task_id": task_id, "assignee_id": assignee.pk}


# ---------------------------------------------------------------------------
# send_team_burnout_notification — manager/admin team burnout change
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.telegram_bot.tasks.send_team_burnout_notification",
    queue="telegram",
)
def send_team_burnout_notification(
    self: Any,
    team_id: int,
    employee_id: int,
    old_level: str,
    new_level: str,
) -> dict:
    """
    Notify managers/admins when an employee burnout change affects team stats.
    """
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role
    from apps.burnout.services import BurnoutService
    from apps.companies.models import Team
    from .notifications import (
        format_burnout_level,
        get_team_notification_recipients,
        send_to_recipients,
        web_url,
    )

    User = get_user_model()

    try:
        team = Team.objects.select_related("company", "manager").get(pk=team_id)
    except Team.DoesNotExist:
        return {"sent": 0, "reason": "team_not_found"}

    try:
        employee = User.objects.get(pk=employee_id, is_active=True, role=Role.EMPLOYEE)
    except User.DoesNotExist:
        return {"sent": 0, "reason": "employee_not_found"}

    summary = BurnoutService.get_team_summary(team)
    if summary.get("total", 0) == 0:
        return {"sent": 0, "reason": "no_consenting_team_data"}

    employee_name = employee.get_full_name() or employee.email
    text = (
        f"📊 <b>Team Burnout Updated</b>\n\n"
        f"👥 Team: <b>{team.name}</b>\n"
        f"👤 <b>{employee_name}</b>\n"
        f"{format_burnout_level(old_level)} → <b>{format_burnout_level(new_level)}</b>\n\n"
        f"<b>Team distribution</b> ({summary['total']} members):\n"
        f"🟢 {summary['green']} · 🟡 {summary['yellow']} · 🔴 {summary['red']}"
    )

    buttons = [
        [
            {"text": "💭 Team Burnout", "url": web_url("burnout:team_summary")},
            {"text": "📊 Dashboard", "url": web_url("accounts:dashboard-manager")},
        ],
    ]

    recipients = get_team_notification_recipients(team)
    sent = send_to_recipients(recipients, text, button_rows=buttons)
    logger.info(
        "send_team_burnout_notification: team_id=%s employee_id=%s sent=%s",
        team_id, employee_id, sent,
    )
    return {"sent": sent, "team_id": team_id, "employee_id": employee_id}


# ---------------------------------------------------------------------------
# send_real_reward_notification — triggered when user receives reward
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="apps.telegram_bot.tasks.send_real_reward_notification", queue="telegram")
def send_real_reward_notification(self: Any, user_id: int, reward_id: int) -> dict:
    """
    Notify user when they receive a real-world reward.
    Only sent if the user has an active Telegram account.
    """
    from .models import TelegramUser
    from .services import TelegramService
    from apps.gamification.models import RealReward

    try:
        reward = RealReward.objects.get(id=reward_id)
    except RealReward.DoesNotExist:
        logger.warning("send_real_reward_notification: reward_id=%s not found", reward_id)
        return {"sent": False, "reason": "reward_not_found"}

    try:
        tg_user = TelegramUser.objects.get(user_id=user_id, is_active=True, telegram_id__gt=0)
    except TelegramUser.DoesNotExist:
        logger.debug("send_real_reward_notification: no active TelegramUser for user_id=%s", user_id)
        return {"sent": False, "reason": "no_telegram_user"}

    reward_type_emojis = {
        "certificate": "📜",
        "bonus": "💰",
        "day_off": "🏖️",
        "custom": "🎁",
    }
    reward_emoji = reward_type_emojis.get(reward.reward_type, "🎁")

    text = (
        f"{reward_emoji} <b>You've Earned a Reward!</b>\n\n"
        f"<b>{reward.get_reward_type_display()}</b>\n"
        f"<i>{reward.description}</i>\n\n"
        f"Granted by: {reward.granted_by.get_full_name() or reward.granted_by.email}\n\n"
        f"Congratulations! 🎉\n\n"
        f"👉 <a href='http://questflow.app/dashboard/'>View your rewards</a>"
    )

    ok = TelegramService.send_message(tg_user.telegram_id, text)
    logger.info(
        "send_real_reward_notification: user_id=%s reward_id=%s sent=%s",
        user_id, reward_id, ok
    )
    return {"sent": ok, "user_id": user_id, "reward_id": reward_id}
