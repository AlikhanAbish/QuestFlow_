from __future__ import annotations

import json
import logging
from asgiref.sync import async_to_sync

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .bot import get_application, process_webhook_update
from .services import TelegramService
from apps.telegram_bot.models import TelegramUser

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    def post(self, request, *args, **kwargs):
        # 🔥 ЖЕСТКИЙ ЛОГ №1: Проверяем, видит ли Django запрос вообще
        print("!!! [TELEGRAM WEBHOOK] -> ПОЛУЧЕН POST ЗАПРОС ОТ ТЕЛЕГРАМА !!!")
        
        try:
            body_unicode = request.body.decode('utf-8')
            print(f"!!! [TELEGRAM WEBHOOK] Тело запроса: {body_unicode}")
            data = json.loads(body_unicode)
        except Exception as e:
            print(f"❌ [TELEGRAM WEBHOOK] Ошибка парсинга JSON: {e}")
            return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

        from telegram import Update
        application = get_application()
        if application is None:
            print("❌ [TELEGRAM WEBHOOK] Application равен None! Проверь TELEGRAM_BOT_TOKEN!")
            return JsonResponse({"ok": False, "error": "Bot not configured"}, status=503)

        try:
            update = Update.de_json(data, application.bot)
            print(f"!!! [TELEGRAM WEBHOOK] Update успешно собран. ID Обновления: {update.update_id if update else 'None'}")
            
            # Отправляем в асинхронный обработчик
            async_to_sync(process_webhook_update)(update)
            print("!!! [TELEGRAM WEBHOOK] -> Обработчик process_webhook_update успешно завершен!")
            
        except Exception as exc:
            print(f"❌❌❌ [TELEGRAM WEBHOOK] КРИТИЧЕСКАЯ ОШИБКА ОБРАБОТКИ: {exc}")
            logger.error("TelegramWebhookView error", exc_info=True)
            return JsonResponse({"ok": False}, status=500)

        return JsonResponse({"ok": True})

    def get(self, request, *args, **kwargs):
        """Health check"""
        return JsonResponse({"status": "ok", "info": "Webhook is alive"})


# ---------------------------------------------------------------------------
# Исправленный Telegram Connect Widget
# ---------------------------------------------------------------------------

class TelegramConnectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return self._render_widget(request)

    def post(self, request, *args, **kwargs):
        return self._render_widget(request, rotate=True)

    def _render_widget(self, request, rotate: bool = False):
        from django.template.response import TemplateResponse
        from django.conf import settings
        from apps.telegram_bot.models import TelegramUser
        import traceback

        # Проверка на случай, если аноним пробрался к урлу
        if not request.user.is_authenticated:
            print("❌ [TELEGRAM WIDGET] Ошибка: Пользователь не авторизован!")
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            # Безопасно берем или создаем запись в БД
            tg_user, created = TelegramUser.objects.get_or_create(user=request.user)
            
            # Генерируем токен
            token = TelegramService.generate_connect_token(request.user)
            bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "QuestFlowBot")
            
            print(f"🍏 [TELEGRAM WIDGET] Успешно сгенерирован токен {token} для юзера {request.user.username}")

            context = {
                "connect_token": token,
                "bot_username": bot_username,
                "deep_link": f"https://t.me/{bot_username}?start={token}",
                "connect_param": token,
                "already_linked": self._is_linked(request.user),
            }
            
        except Exception as e:
            print(f"❌❌❌ [TELEGRAM WIDGET] КРИТИЧЕСКИЙ СБОЙ ВНУТРИ ВИДЖЕТА: {e}")
            print(traceback.format_exc())
            return HttpResponse("<p style='color:red;'>Ошибка загрузки виджета Телеграм</p>", status=200)

        template = "telegram_bot/partials/_connect_widget.html"
        return TemplateResponse(request, template, context)

    @staticmethod
    def _is_linked(user) -> bool:
        try:
            return user.telegram.is_active and user.telegram.telegram_id is not None
        except Exception:
            return False