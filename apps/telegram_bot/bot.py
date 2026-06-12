import logging
from django.conf import settings

# Импортируем типы из python-telegram-bot
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

# Глобальный синглтон приложения
_application = None

def get_application():
    """
    Инициализирует асинхронный Application и регистрирует хэндлеры через handlers.py
    """
    global _application
    if _application is None:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token or token == "your-telegram-bot-token":
            logger.error("🤖 [BOT CONFIG] TELEGRAM_BOT_TOKEN не установлен!")
            return None
        
        try:
            # Собираем инстанс Application
            builder = Application.builder().token(token)
            _application = builder.build()
            
            # 🔥 Вызываем твою готовую функцию регистрации!
            from .handlers import register_handlers
            register_handlers(_application)
            
            logger.info("🤖 [BOT CONFIG] Бот и все хэндлеры успешно инициализированы.")
        except Exception as e:
            logger.error(f"🤖 [BOT CONFIG] Критическая ошибка сборки Application: {e}", exc_info=True)
            return None
            
    return _application


async def process_webhook_update(update: Update):
    """
    Проталкивает пришедший вебхук внутрь хэндлеров Telegram.
    """
    application = get_application()
    if not application:
        print("❌ [BOT PROCESS] Сбой: Application равен None.")
        return

    try:
        # Прогреваем контекст бота для работы внутри Gunicorn веб-воркеров
        if not application.running:
            await application.initialize()
            await application.start()
            print("🍏 [BOT PROCESS] Контекст Telegram-приложения успешно запущен.")

        # Передаем распарсенное событие в хэндлеры
        await application.process_update(update)
        print(f"🍏 [BOT PROCESS] Вебхук ID {update.update_id} обработан без ошибок.")
        
    except Exception as e:
        print(f"❌ [BOT PROCESS] Ошибка внутри process_webhook_update: {e}")
        logger.error("Ошибка обработки апдейта", exc_info=True)