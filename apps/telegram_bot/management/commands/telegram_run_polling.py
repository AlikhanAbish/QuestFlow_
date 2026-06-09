"""
Local development: receive updates via long polling (no public webhook required).

Usage:
    docker compose exec django python manage.py telegram_run_polling
"""
import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import Application


class Command(BaseCommand):
    help = "Run Telegram bot in polling mode (for local dev without ngrok)."

    def handle(self, *args, **options):
        from apps.telegram_bot.bot import delete_webhook
        from apps.telegram_bot.handlers import register_handlers

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token or token == "your-telegram-bot-token":
            self.stderr.write(
                self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured in .env")
            )
            return

        if delete_webhook():
            self.stdout.write("Previous webhook removed.")
        else:
            self.stdout.write("No webhook removed (API error or none set).")

        application = Application.builder().token(token).build()
        register_handlers(application)

        self.stdout.write(
            self.style.SUCCESS("Polling started. Send /start to your bot. Ctrl+C to stop.")
        )
        asyncio.run(
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
        )
