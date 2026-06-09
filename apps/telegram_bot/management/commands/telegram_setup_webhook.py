from django.core.management.base import BaseCommand

from apps.telegram_bot.bot import setup_webhook, _is_local_webhook_url
from django.conf import settings


class Command(BaseCommand):
    help = "Register TELEGRAM_WEBHOOK_URL with Telegram (must be public HTTPS)."

    def handle(self, *args, **options):
        url = getattr(settings, "TELEGRAM_WEBHOOK_URL", "")
        if not url:
            self.stderr.write(self.style.ERROR("TELEGRAM_WEBHOOK_URL is not set in .env"))
            return

        if _is_local_webhook_url(url):
            self.stderr.write(
                self.style.ERROR(
                    f"Cannot use local URL for Telegram webhook: {url}\n"
                    "Telegram servers cannot reach localhost.\n"
                    "  1) Expose your app via ngrok and set TELEGRAM_WEBHOOK_URL=https://xxx.ngrok.io/telegram/webhook/\n"
                    "  2) For local dev use: python manage.py telegram_run_polling"
                )
            )
            return

        if setup_webhook():
            self.stdout.write(self.style.SUCCESS(f"Webhook registered: {url}"))
        else:
            self.stderr.write(self.style.ERROR("Failed to register webhook. Check logs and TELEGRAM_BOT_TOKEN."))
