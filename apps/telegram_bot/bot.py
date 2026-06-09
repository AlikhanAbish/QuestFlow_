"""
bot.py — python-telegram-bot Application setup.

Provides:
  get_application() — returns a shared Application singleton (used by webhook view)
  get_bot()         — returns the Bot object for direct API calls
  ensure_application_started() — initialize + start (required before process_update)
  process_webhook_update()     — handle a single Update from Django webhook
  setup_webhook()   — registers the webhook URL with Telegram
"""
from __future__ import annotations

import asyncio
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_application = None
_start_lock: asyncio.Lock | None = None


def _get_start_lock() -> asyncio.Lock:
    global _start_lock
    if _start_lock is None:
        _start_lock = asyncio.Lock()
    return _start_lock


def get_application():
    """
    Returns (and lazily creates) the shared python-telegram-bot Application.
    Uses updater=None for custom Django webhook (see PTB customwebhookbot example).
    """
    global _application

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or token == "your-telegram-bot-token":
        logger.debug("get_application: TELEGRAM_BOT_TOKEN not set — bot disabled.")
        return None

    if _application is None:
        from telegram.ext import Application
        from .handlers import register_handlers

        _application = (
            Application.builder()
            .token(token)
            .updater(None)
            .build()
        )
        register_handlers(_application)
        logger.info("Telegram Application created and handlers registered.")

    return _application


async def ensure_application_started() -> bool:
    """
    PTB requires initialize() + start() before process_update() works.
    Safe to call on every webhook request (guarded by lock).
    """
    application = get_application()
    if application is None:
        return False

    if application.running:
        return True

    async with _get_start_lock():
        if not application.initialized:
            await application.initialize()
        if not application.running:
            await application.start()
            logger.info("Telegram Application started for webhook processing.")

    return True


async def process_webhook_update(update) -> None:
    """Process one Telegram update through registered handlers."""
    if not await ensure_application_started():
        raise RuntimeError("Telegram bot is not configured")
    application = get_application()
    await application.process_update(update)


def get_bot():
    """Return the Bot instance, or None if not configured."""
    app = get_application()
    return app.bot if app else None


def setup_webhook() -> bool:
    """
    Register the webhook URL with Telegram's Bot API.
    Returns True on success.
    """
    import httpx

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    webhook_url = getattr(settings, "TELEGRAM_WEBHOOK_URL", None)

    if not token or token == "your-telegram-bot-token":
        logger.warning("setup_webhook: TELEGRAM_BOT_TOKEN not configured.")
        return False
    if not webhook_url:
        logger.warning("setup_webhook: TELEGRAM_WEBHOOK_URL not configured.")
        return False

    if _is_local_webhook_url(webhook_url):
        logger.error(
            "setup_webhook: TELEGRAM_WEBHOOK_URL must be a public HTTPS URL. "
            "Telegram cannot reach localhost. Use ngrok or run: "
            "python manage.py telegram_run_polling"
        )
        return False

    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        resp = httpx.post(
            url,
            json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("Webhook set to: %s", webhook_url)
            return True
        logger.error("setWebhook failed: %s", data)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("setup_webhook exception: %s", exc)
        return False


def delete_webhook() -> bool:
    """Remove webhook (required before polling in dev)."""
    import httpx

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or token == "your-telegram-bot-token":
        return False

    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    try:
        resp = httpx.post(url, json={"drop_pending_updates": True}, timeout=10)
        data = resp.json()
        return bool(data.get("ok"))
    except Exception as exc:  # noqa: BLE001
        logger.error("delete_webhook exception: %s", exc)
        return False


def _is_local_webhook_url(webhook_url: str) -> bool:
    lowered = webhook_url.lower()
    return any(
        host in lowered
        for host in (
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "host.docker.internal",
        )
    )
