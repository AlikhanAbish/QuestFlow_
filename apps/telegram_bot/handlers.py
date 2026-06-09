"""
handlers.py — Telegram command and message handlers.

Commands:
  /start [token]  — link Telegram account to QuestFlow profile
  /help           — show available commands
  /profile        — display user's level, XP, streak (role-aware)
  /tasks          — show active tasks (role-aware)
  /badges         — show earned badges

All handlers are async coroutines as required by python-telegram-bot v20+.
"""
from __future__ import annotations

import logging

from django.db.models import Q
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.accounts.models import Role
from .services import TelegramService

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    Role.EMPLOYEE: "Employee",
    Role.MANAGER: "Manager",
    Role.ADMIN: "Admin",
}

BURNOUT_LABELS = {
    "green": "🟢 Healthy",
    "yellow": "🟡 At Risk",
    "red": "🔴 Burned Out",
}


def is_manager_or_admin(role: str) -> bool:
    return role in (Role.MANAGER, Role.ADMIN)


def get_team_for_user(user) -> object | None:
    """Resolve the team used for manager/admin team stats."""
    if user.role == Role.MANAGER:
        managed = user.managed_teams.first()
        if managed:
            return managed
    return getattr(user, "team", None)


# ---------------------------------------------------------------------------
# Sync Helpers for Async Context
# ---------------------------------------------------------------------------

def _get_user_burnout_text(user) -> str:
    try:
        score = user.burnout_score
        return BURNOUT_LABELS.get(score.score, "❓ Not assessed")
    except Exception:
        return "❓ Not assessed"


def _get_user_level_stats(user) -> tuple[int, int, int]:
    try:
        level_data = user.level_data
        return level_data.level, level_data.total_xp, level_data.weekly_xp
    except Exception:
        return 1, 0, 0


def _get_user_streak(user) -> int:
    try:
        return user.streak.current
    except Exception:
        return 0


def _build_task_entry(task, *, include_assignee: bool = False) -> dict:
    deadline_text = ""
    if task.deadline:
        delta = task.deadline - timezone.now()
        if delta.days < 0:
            deadline_text = " <u>OVERDUE!</u>"
        elif delta.days == 0:
            deadline_text = " 🚨 Today"
        elif delta.days == 1:
            deadline_text = " 📅 Tomorrow"
        else:
            deadline_text = f" 📅 {delta.days}d"

    entry = {
        "title": task.title,
        "priority": task.priority,
        "status": task.status,
        "deadline_text": deadline_text,
        "team_name": task.team.name if task.team else None,
    }
    if include_assignee:
        assignee = task.assigned_to
        entry["assignee"] = (
            assignee.get_full_name() or assignee.email if assignee else "Unassigned"
        )
    return entry


def _get_team_profile_extras(user) -> dict:
    from apps.analytics.services import AnalyticsService
    from apps.burnout.services import BurnoutService
    from apps.gamification.services import LeaderboardService

    extras = {
        "leaderboard": LeaderboardService.get_company_leaderboard(
            company=getattr(user, "company", None),
            current_user_id=user.id,
            limit=5,
        ),
        "team_name": None,
        "burnout_stats": None,
        "team_summary": None,
    }

    team = get_team_for_user(user)
    if team:
        extras["team_name"] = team.name
        extras["burnout_stats"] = BurnoutService.get_team_summary(team)
        extras["team_summary"] = AnalyticsService.get_summary_stats(team)

    return extras


def get_profile_data(tg_id: int) -> dict | None:
    from .models import TelegramUser
    try:
        tg_user = TelegramUser.objects.select_related(
            "user__level_data",
            "user__streak",
            "user__burnout_score",
            "user__company",
            "user__team",
        ).get(telegram_id=tg_id, is_active=True)
    except TelegramUser.DoesNotExist:
        return None

    user = tg_user.user
    name = user.get_full_name() or user.email
    level, total_xp, weekly_xp = _get_user_level_stats(user)

    profile = {
        "name": name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role.title()),
        "level": level,
        "total_xp": total_xp,
        "weekly_xp": weekly_xp,
        "streak": _get_user_streak(user),
        "burnout_text": _get_user_burnout_text(user),
    }

    if is_manager_or_admin(user.role):
        profile.update(_get_team_profile_extras(user))

    return profile


def get_tasks_data(tg_id: int) -> dict | None:
    from .models import TelegramUser
    from apps.tasks.models import Task, TaskStatus

    try:
        tg_user = TelegramUser.objects.select_related(
            "user", "user__company"
        ).get(telegram_id=tg_id, is_active=True)
    except TelegramUser.DoesNotExist:
        return None

    user = tg_user.user
    qs = Task.objects.filter(
        is_deleted=False,
        status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
    )

    if user.role == Role.EMPLOYEE:
        qs = qs.filter(assigned_to=user)
    elif user.role == Role.MANAGER:
        qs = qs.filter(
            Q(assigned_to__team__manager=user) | Q(created_by=user)
        )
    elif user.company_id:
        qs = qs.filter(company=user.company)

    tasks = list(
        qs.order_by("deadline", "priority")
        .select_related("team", "assigned_to")[:10]
    )

    include_assignee = is_manager_or_admin(user.role)
    task_list = [
        _build_task_entry(task, include_assignee=include_assignee) for task in tasks
    ]

    return {
        "role": user.role,
        "tasks": task_list,
    }


def get_badges_data(tg_id: int) -> list[dict] | None:
    from .models import TelegramUser
    from apps.gamification.models import UserBadge

    try:
        tg_user = TelegramUser.objects.select_related("user").get(
            telegram_id=tg_id, is_active=True
        )
    except TelegramUser.DoesNotExist:
        return None

    user = tg_user.user
    badges = list(UserBadge.objects.filter(user=user).select_related("badge").order_by("-created_at")[:15])

    badge_list = []
    for ub in badges:
        badge_list.append({
            "name": ub.badge.name,
            "description": ub.badge.description,
            "earned_date": ub.created_at.strftime("%b %d, %Y"),
        })
    return badge_list


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

def format_employee_stats_block(profile_data: dict, *, detailed: bool = False) -> str:
    """Personal gamification stats — shown only to employees."""
    lines = [
        f"🏆 Level: <b>{profile_data['level']}</b>\n",
    ]
    if detailed:
        lines.extend([
            f"⚡ Total XP: <b>{profile_data['total_xp']:,}</b>\n",
            f"📅 Weekly XP: <b>{profile_data['weekly_xp']:,}</b>\n",
        ])
    lines.extend([
        f"🔥 Streak: <b>{profile_data['streak']} day(s)</b>\n",
        f"💭 Burnout: {profile_data['burnout_text']}\n",
    ])
    return "".join(lines)


def format_start_profile_summary(profile_data: dict) -> str:
    """Short stats block for /start when the Telegram account is already linked."""
    header = (
        f"<b>👤 {profile_data['name']}</b> · {profile_data['role_label']}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )
    if is_manager_or_admin(profile_data["role"]):
        body = (
            format_team_leaderboard_section(profile_data.get("leaderboard", []))
            + format_team_burnout_section(profile_data.get("burnout_stats"))
            + format_team_summary_section(
                profile_data.get("team_name"),
                profile_data.get("team_summary"),
            )
        )
        if not body.strip():
            body = "Use /profile for team overview.\n"
    else:
        body = format_employee_stats_block(profile_data)
    return header + body + "━━━━━━━━━━━━━━━━\n"


def format_team_leaderboard_section(leaderboard: list[dict]) -> str:
    if not leaderboard:
        return ""
    lines = ["\n<b>🏅 Team Leaderboard</b>"]
    for entry in leaderboard:
        marker = " ← you" if entry.get("is_me") else ""
        lines.append(
            f"{entry['rank']}. {entry['name']} — Lv.{entry['level']} · {entry['xp']:,} XP{marker}"
        )
    return "\n".join(lines) + "\n"


def format_team_burnout_section(burnout_stats: dict | None) -> str:
    if not burnout_stats or burnout_stats.get("total", 0) == 0:
        return "\n<b>💭 Team Burnout</b>\nNo consenting team data yet.\n"
    return (
        f"\n<b>💭 Team Burnout</b> ({burnout_stats['total']} members)\n"
        f"🟢 {burnout_stats['green']} · "
        f"🟡 {burnout_stats['yellow']} · "
        f"🔴 {burnout_stats['red']}\n"
    )


def format_team_summary_section(team_name: str | None, summary: dict | None) -> str:
    if not summary:
        return ""
    team_label = f" — {team_name}" if team_name else ""
    return (
        f"\n<b>📊 Team Stats{team_label}</b>\n"
        f"👥 Members: <b>{summary['total_members']}</b>\n"
        f"📋 Active: <b>{summary['active_tasks']}</b> · "
        f"✅ Done: <b>{summary['done_tasks']}</b> · "
        f"⚠️ Overdue: <b>{summary['overdue_tasks']}</b>\n"
        f"⚡ Team XP: <b>{summary['total_xp']:,}</b>\n"
    )


def format_profile_message(profile_data: dict) -> str:
    text = (
        f"<b>👤 {profile_data['name']}</b> · {profile_data['role_label']}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )

    if is_manager_or_admin(profile_data["role"]):
        text += format_team_leaderboard_section(profile_data.get("leaderboard", []))
        text += format_team_burnout_section(profile_data.get("burnout_stats"))
        text += format_team_summary_section(
            profile_data.get("team_name"),
            profile_data.get("team_summary"),
        )
    else:
        text += format_employee_stats_block(profile_data, detailed=True)

    return text.rstrip() + "\n"


def build_tasks_keyboard(role: str) -> InlineKeyboardMarkup:
    rows = []
    if is_manager_or_admin(role):
        rows.append([
            InlineKeyboardButton("➕ Create Task", url="http://questflow.app/tasks/create/"),
        ])
    rows.append([
        InlineKeyboardButton("📊 Dashboard", url="http://questflow.app/dashboard/"),
    ])
    return InlineKeyboardMarkup(rows)


def format_tasks_message(tasks_data: dict) -> str:
    from apps.tasks.models import TaskStatus

    role = tasks_data["role"]
    tasks = tasks_data["tasks"]
    is_team_view = is_manager_or_admin(role)

    if is_team_view:
        header = "📋 <b>Team Active Tasks</b>\n\n"
        empty_text = (
            "📋 <b>Team Active Tasks</b>\n\n"
            "No active tasks in your scope. 🎉"
        )
    else:
        header = "📋 <b>Your Active Tasks</b>\n\n"
        empty_text = (
            "📋 <b>Your Tasks</b>\n\n"
            "You have no active tasks! 🎉"
        )

    if not tasks:
        return empty_text

    priority_emojis = {1: "🟢", 2: "🟡", 3: "🔴", 4: "⚫"}
    lines = [header]

    for i, task in enumerate(tasks, 1):
        priority_emoji = priority_emojis.get(task["priority"], "⚪")
        status_emoji = "📝" if task["status"] == TaskStatus.TODO else "⚙️"
        team_name = f" [{task['team_name']}]" if task["team_name"] else ""
        assignee = ""
        if is_team_view and task.get("assignee"):
            assignee = f" — <i>{task['assignee']}</i>"
        lines.append(
            f"{i}. {priority_emoji} {status_emoji} <b>{task['title']}</b>"
            f"{assignee}{team_name}{task['deadline_text']}\n"
        )

    lines.append("\n👉 <a href='http://questflow.app/tasks/'>View all tasks</a>")
    return "".join(lines)


def format_link_onboarding_message() -> str:
    """Instructions for users who have not linked Telegram yet."""
    return (
        "👋 <b>Welcome to QuestFlow Bot!</b>\n\n"
        "Link your QuestFlow account to get reminders and alerts:\n"
        "1. Open your profile on the web: <code>/profile/</code>\n"
        "2. Go to the <b>Telegram Integration</b> section\n"
        "3. Click <b>Connect Telegram</b> or <b>Open in Telegram</b>\n\n"
        "After linking, use /profile for full stats, /tasks and /help."
    )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start [token]

    With a token: links the Telegram account to the QuestFlow user who owns that token.
    Without a token: shows profile summary if linked, otherwise onboarding steps.
    """
    message = update.effective_message
    if not message:
        logger.warning("start_handler: update %s has no message", update.update_id)
        return

    args = context.args or []
    tg_user = update.effective_user

    if args:
        token = args[0]
        linked = await sync_to_async(TelegramService.link_account)(
            token=token,
            telegram_id=tg_user.id,
            username=tg_user.username or "",
            first_name=tg_user.first_name or "",
        )
        if linked:
            profile_data = await sync_to_async(get_profile_data)(tg_user.id)
            if profile_data:
                role_hint = ""
                if is_manager_or_admin(profile_data["role"]):
                    role_hint = (
                        "\nAs a Manager/Admin you can view team leaderboard, "
                        "burnout and subordinate tasks via /profile and /tasks."
                    )
                await message.reply_html(
                    "✅ <b>Account linked!</b>\n\n"
                    + format_start_profile_summary(profile_data)
                    + "\nYou will receive daily reminders and burnout alerts."
                    + role_hint
                    + "\nUse /profile for full stats, /tasks for active tasks."
                )
            else:
                user = linked.user
                name = user.first_name or user.email
                role_label = ROLE_LABELS.get(user.role, user.role.title())
                await message.reply_html(
                    f"✅ <b>Account linked!</b>\n\n"
                    f"Welcome to QuestFlow, <b>{name}</b>! 🎮\n"
                    f"Role: <b>{role_label}</b>\n\n"
                    f"You will now receive:\n"
                    f"• ☀️ Daily morning reminders\n"
                    f"• 📝 Weekly self-assessment alerts\n"
                    f"• 🔥 Burnout status change notifications\n\n"
                    f"Use /profile to check your progress."
                )
        else:
            await message.reply_html(
                "❌ Invalid or expired link token.\n\n"
                "Open your QuestFlow profile and generate a new link:\n"
                "👉 <code>/profile/</code> → Telegram Integration → <b>Connect Telegram</b>"
            )
    else:
        profile_data = await sync_to_async(get_profile_data)(tg_user.id)
        if profile_data:
            await message.reply_html(
                "👋 <b>Welcome back to QuestFlow!</b>\n\n"
                + format_start_profile_summary(profile_data)
                + "\nUse /profile for full stats · /tasks · /help"
            )
        else:
            await message.reply_html(format_link_onboarding_message())


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — list available commands."""
    tg_id = update.effective_user.id
    profile_data = await sync_to_async(get_profile_data)(tg_id)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Dashboard", url="http://questflow.app/dashboard/"),
    ]])

    tasks_hint = "/tasks — Show your active tasks"
    profile_hint = "/profile — View your level, XP and streak"
    if profile_data and is_manager_or_admin(profile_data["role"]):
        profile_hint = "/profile — Your stats + team leaderboard & burnout"
        tasks_hint = "/tasks — Team tasks (create & manage on web)"

    await update.message.reply_html(
        "<b>QuestFlow Bot — Commands</b>\n\n"
        "/start <code>[token]</code> — Link your QuestFlow account\n"
        f"{profile_hint}\n"
        f"{tasks_hint}\n"
        "/badges — Show your earned badges\n"
        "/help — Show this message\n\n"
        "🌐 <a href='http://questflow.app'>Open QuestFlow</a>",
        reply_markup=keyboard
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/profile — show the linked user's gamification stats."""
    tg_id = update.effective_user.id

    profile_data = await sync_to_async(get_profile_data)(tg_id)
    if not profile_data:
        await update.message.reply_text(
            "⚠️ Your Telegram account is not linked to any QuestFlow account.\n"
            "Use /start <token> after getting a link from your profile page."
        )
        return

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Tasks", callback_data="show_tasks"),
        InlineKeyboardButton("🏅 Badges", callback_data="show_badges"),
    ], [
        InlineKeyboardButton("📊 Dashboard", url="http://questflow.app/dashboard/"),
    ]])

    await update.message.reply_html(
        format_profile_message(profile_data),
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# /tasks
# ---------------------------------------------------------------------------

async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tasks — show active tasks (own tasks for employees, team scope for managers)."""
    tg_id = update.effective_user.id

    tasks_data = await sync_to_async(get_tasks_data)(tg_id)
    if tasks_data is None:
        await update.message.reply_text(
            "⚠️ Your Telegram account is not linked to any QuestFlow account.\n"
            "Use /start <token> after getting a link from your profile page."
        )
        return

    text = format_tasks_message(tasks_data)
    keyboard = build_tasks_keyboard(tasks_data["role"])
    await update.message.reply_html(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# /badges
# ---------------------------------------------------------------------------

async def badges_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/badges — show user's earned badges."""
    tg_id = update.effective_user.id

    badges = await sync_to_async(get_badges_data)(tg_id)
    if badges is None:
        await update.message.reply_text(
            "⚠️ Your Telegram account is not linked to any QuestFlow account.\n"
            "Use /start <token> after getting a link from your profile page."
        )
        return

    if not badges:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Dashboard", url="http://questflow.app/dashboard/"),
        ]])
        await update.message.reply_html(
            "🏅 <b>Your Badges</b>\n\n"
            "You haven't earned any badges yet! 🚀\n\n"
            "Keep completing tasks and leveling up to earn badges.",
            reply_markup=keyboard
        )
        return

    # Format badges
    text = "🏅 <b>Your Badges</b>\n\n"

    for i, badge in enumerate(badges, 1):
        text += f"{i}. 🎖️ <b>{badge['name']}</b>\n"
        text += f"   <i>{badge['description']}</i>\n"
        text += f"   📅 Earned: {badge['earned_date']}\n\n"

    text += f"<b>Total Badges:</b> {len(badges)}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Dashboard", url="http://questflow.app/dashboard/"),
    ]])

    await update.message.reply_html(text, reply_markup=keyboard)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log handler exceptions so webhook failures are visible in Django logs."""
    logger.error(
        "Telegram handler error (update=%s): %s",
        update,
        context.error,
        exc_info=context.error,
    )


def register_handlers(application: Application) -> None:
    """Register all command handlers onto the Application."""
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("profile", profile_handler))
    application.add_handler(CommandHandler("tasks", tasks_handler))
    application.add_handler(CommandHandler("badges", badges_handler))
    application.add_error_handler(error_handler)
    logger.debug("Telegram handlers registered: /start /help /profile /tasks /badges")
