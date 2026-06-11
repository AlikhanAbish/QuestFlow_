from django.apps import AppConfig
import sys

class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telegram_bot'

    def ready(self):
        # Защита: не регистрируем вебхук во время миграций, сбора статики или тестов
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test']):
            return

        # Импортируем внутри метода, чтобы избежать циклической зависимости
        from apps.telegram_bot.services import TelegramService
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Вызываем метод установки вебхука
            # Убедись, что такой метод или аналогичный есть в твоем TelegramService
            success = TelegramService.setup_webhook() 
            if success:
                logger.info("🤖 [TELEGRAM] Вебхук успешно зарегистрирован в Telegram API.")
            else:
                logger.error("🤖 [TELEGRAM] Не удалось зарегистрировать вебхук.")
        except Exception as e:
            logger.error(f"🤖 [TELEGRAM] Ошибка при автоматической установке вебхука: {e}")