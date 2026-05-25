"""
views.py — Telegram Bot views.

TelegramWebhookView   POST /telegram/webhook/
    Receives Telegram Update JSON, dispatches to Application handlers.
    CSRF exempt (Telegram sends no CSRF token).

TelegramConnectView   POST /profile/telegram/connect/
    HTMX: generates/rotates connect_token for the current user,
    returns a partial with instructions + deep-link button.
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .services import TelegramService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    TZ 4.9: POST /telegram/webhook/

    Receives raw JSON from Telegram and processes it through the
    python-telegram-bot Application using its synchronous process_update
    interface (compatible with Django's sync WSGI without asyncio loops).
    """

    async def post(self, request, *args, **kwargs):
        from telegram import Update
        from .bot import get_application

        application = get_application()
        if application is None:
            logger.warning("TelegramWebhookView: bot not configured.")
            return JsonResponse({"ok": False, "error": "Bot not configured"}, status=503)

        try:
            data = json.loads(request.body)
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
        except Exception as exc:
            logger.error("TelegramWebhookView error: %s", exc, exc_info=True)
            return JsonResponse({"ok": False}, status=500)

        return JsonResponse({"ok": True})

    async def get(self, request, *args, **kwargs):
        """Health-check endpoint."""
        from django.conf import settings
        token_set = bool(
            getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            and settings.TELEGRAM_BOT_TOKEN != "your-telegram-bot-token"
        )
        return JsonResponse({"status": "ok", "bot_configured": token_set})


# ---------------------------------------------------------------------------
# Telegram Connect (HTMX)
# ---------------------------------------------------------------------------

class TelegramConnectView(LoginRequiredMixin, View):
    """
    TZ 4.1: POST /profile/telegram/connect/

    Generates a fresh connect_token and returns the partial with the deep-link.
    On GET, returns the same partial (used for initial load via hx-get).
    """

    def get(self, request, *args, **kwargs):
        return self._render_widget(request)

    def post(self, request, *args, **kwargs):
        return self._render_widget(request, rotate=True)

    def _render_widget(self, request, rotate: bool = False):
        from django.template.response import TemplateResponse
        from django.conf import settings

        token = TelegramService.generate_connect_token(request.user)
        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "QuestFlowBot")

        context = {
            "connect_token": token,
            "bot_username": bot_username,
            "deep_link": f"https://t.me/{bot_username}?start={token}",
            "already_linked": self._is_linked(request.user),
        }

        template = "telegram_bot/partials/_connect_widget.html"
        return TemplateResponse(request, template, context)

    @staticmethod
    def _is_linked(user) -> bool:
        try:
            return user.telegram.is_active and user.telegram.telegram_id > 0
        except Exception:
            return False
