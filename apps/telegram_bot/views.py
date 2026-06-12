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
from asgiref.sync import async_to_sync  # 🔥 Добавили мост между sync и async

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.mixins import LoginRequiredMixin

from .bot import get_application, process_webhook_update

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    POST /telegram/webhook/
    Преобразует синхронный запрос Django в безопасную асинхронную среду
    без создания конфликтующих event loop'ов.
    """

    def post(self, request, *args, **kwargs):
        from telegram import Update

        application = get_application()
        if application is None:
            logger.warning("TelegramWebhookView: bot not configured.")
            return JsonResponse({"ok": False, "error": "Bot not configured"}, status=503)

        try:
            # Читаем и парсим тело запроса
            data = json.loads(request.body)
            update = Update.de_json(data, application.bot)
            
            if update is None:
                logger.warning("TelegramWebhookView: failed to parse update.")
                return JsonResponse({"ok": False, "error": "Invalid update"}, status=400)

            # 🔥 Безопасно вызываем асинхронную обработку внутри веб-потока Gunicorn
            async_to_sync(process_webhook_update)(update)

        except Exception as exc:
            logger.error("TelegramWebhookView error: %s", exc, exc_info=True)
            return JsonResponse({"ok": False}, status=500)

        return JsonResponse({"ok": True})

    def get(self, request, *args, **kwargs):
        """Health-check endpoint (оставляем без изменений)"""
        from django.conf import settings
        from .bot import _is_local_webhook_url

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        webhook_url = getattr(settings, "TELEGRAM_WEBHOOK_URL", "")
        token_set = bool(token and token != "your-telegram-bot-token")
        webhook_public = bool(webhook_url) and not _is_local_webhook_url(webhook_url)

        return JsonResponse({
            "status": "ok",
            "bot_configured": token_set,
            "webhook_reachable_by_telegram": webhook_public,
            "hint": None if webhook_public else "TELEGRAM_WEBHOOK_URL error",
        })


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
        from apps.telegram_bot.models import TelegramUser  # Импортируем модель

        # 🔥 БЕЗОПАСНО: Проверяем существование или создаем пустую запись TelegramUser для юзера
        tg_user, created = TelegramUser.objects.get_or_create(user=request.user)

        # Генерируем токен (убедись, что метод принимает tg_user или генерирует внутри)
        token = TelegramService.generate_connect_token(request.user)
        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "QuestFlowBot")

        context = {
            "connect_token": token,
            "bot_username": bot_username,
            "deep_link": f"https://t.me/{bot_username}?start={token}",
            "connect_param": token,
            "already_linked": self._is_linked(request.user),
        }

        template = "telegram_bot/partials/_connect_widget.html"
        return TemplateResponse(request, template, context)

    @staticmethod
    def _is_linked(user) -> bool:
        try:
            tg = user.telegram
            return tg.is_active and tg.telegram_id is not None and tg.telegram_id > 0
        except Exception:
            return False
