"""
bot.py — python-telegram-bot Application setup.

Provides:
  get_application() — returns a shared Application singleton (used by webhook view)
  get_bot()         — returns the Bot object for direct API calls
  setup_webhook()   — registers the webhook URL with Telegram
"""
from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_application = None  # Module-level singleton


def get_application():
    """
    Returns (and lazily creates) the shared python-telegram-bot Application.
    Called lazily so Django can start even without a valid token.
    """
    global _application

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or token == "your-telegram-bot-token":
        logger.debug("get_application: TELEGRAM_BOT_TOKEN not set — bot disabled.")
        return None

    if _application is None:
        from telegram.ext import Application
        from .handlers import register_handlers

        builder = Application.builder().token(token)
        _application = builder.build()
        register_handlers(_application)
        logger.info("Telegram Application created and handlers registered.")

    return _application


def get_bot():
    """Return the Bot instance, or None if not configured."""
    app = get_application()
    return app.bot if app else None


def setup_webhook() -> bool:
    """
    Register the webhook URL with Telegram's Bot API.
    Called from a management command or AppConfig.ready().
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

    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        resp = httpx.post(url, json={"url": webhook_url}, timeout=10)
        data = resp.json()
        if data.get("ok"):
            logger.info("Webhook set to: %s", webhook_url)
            return True
        logger.error("setWebhook failed: %s", data)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("setup_webhook exception: %s", exc)
        return False
