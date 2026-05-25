"""
handlers.py — Telegram command and message handlers.

Commands:
  /start [token]  — link Telegram account to QuestFlow profile
  /help           — show available commands
  /profile        — display user's level, XP, streak

All handlers are async coroutines as required by python-telegram-bot v20+.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .services import TelegramService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start [token]

    With a token: links the Telegram account to the QuestFlow user who owns that token.
    Without a token: shows a greeting and instructions.
    """
    args = context.args or []
    tg_user = update.effective_user

    if args:
        token = args[0]
        linked = TelegramService.link_account(
            token=token,
            telegram_id=tg_user.id,
            username=tg_user.username or "",
            first_name=tg_user.first_name or "",
        )
        if linked:
            name = linked.user.first_name or linked.user.email
            await update.message.reply_html(
                f"✅ <b>Account linked!</b>\n\n"
                f"Welcome to QuestFlow, <b>{name}</b>! 🎮\n\n"
                f"You will now receive:\n"
                f"• ☀️ Daily morning reminders\n"
                f"• 📝 Weekly self-assessment alerts\n"
                f"• 🔥 Burnout status change notifications\n\n"
                f"Use /profile to check your progress."
            )
        else:
            await update.message.reply_text(
                "❌ Invalid or expired link token.\n\n"
                "Please visit your QuestFlow profile and generate a new link:\n"
                "👉 /profile/ → Telegram section → Connect"
            )
    else:
        await update.message.reply_html(
            "👋 <b>Welcome to QuestFlow Bot!</b>\n\n"
            "To link your Telegram account:\n"
            "1. Open your QuestFlow profile: <code>/profile/</code>\n"
            "2. Navigate to the <b>Telegram</b> section\n"
            "3. Click <b>Connect Telegram</b> to get your link\n\n"
            "Already linked? Use /profile to check your stats."
        )


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — list available commands."""
    await update.message.reply_html(
        "<b>QuestFlow Bot — Commands</b>\n\n"
        "/start <code>[token]</code> — Link your QuestFlow account\n"
        "/profile — View your level, XP and streak\n"
        "/help — Show this message\n\n"
        "🌐 <a href='http://questflow.app'>Open QuestFlow</a>"
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/profile — show the linked user's gamification stats."""
    from .models import TelegramUser

    tg_id = update.effective_user.id

    try:
        tg_user = TelegramUser.objects.select_related(
            "user__level_data", "user__streak"
        ).get(telegram_id=tg_id, is_active=True)
    except TelegramUser.DoesNotExist:
        await update.message.reply_text(
            "⚠️ Your Telegram account is not linked to any QuestFlow account.\n"
            "Use /start <token> after getting a link from your profile page."
        )
        return

    user = tg_user.user
    name = user.get_full_name() or user.email

    # Gamification stats (graceful fallback if not yet initialised)
    try:
        level_data = user.level_data
        level = level_data.level
        total_xp = level_data.total_xp
        weekly_xp = level_data.weekly_xp
    except Exception:
        level, total_xp, weekly_xp = 1, 0, 0

    try:
        streak = user.streak.current
    except Exception:
        streak = 0

    # Burnout badge (privacy: only shown to the user themselves)
    try:
        score = user.burnout_score
        burnout_labels = {"green": "🟢 Healthy", "yellow": "🟡 At Risk", "red": "🔴 Burned Out"}
        burnout_text = burnout_labels.get(score.score, "❓ Not assessed")
    except Exception:
        burnout_text = "❓ Not assessed"

    await update.message.reply_html(
        f"<b>👤 {name}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🏆 Level: <b>{level}</b>\n"
        f"⚡ Total XP: <b>{total_xp:,}</b>\n"
        f"📅 Weekly XP: <b>{weekly_xp:,}</b>\n"
        f"🔥 Streak: <b>{streak} day(s)</b>\n"
        f"💭 Burnout: {burnout_text}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<a href='http://questflow.app/dashboard/'>Open Dashboard</a>"
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_handlers(application: Application) -> None:
    """Register all command handlers onto the Application."""
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("profile", profile_handler))
    logger.debug("Telegram handlers registered: /start /help /profile")
