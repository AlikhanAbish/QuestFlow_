from django.apps import AppConfig
import sys

class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telegram_bot'

    def ready(self):
        # Защита от выполнения при миграциях и сборе статики
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test']):
            return

        # ИМПОРТИРУЕМ НАПРЯМУЮ ИЗ bot.py
        from apps.telegram_bot.bot import setup_webhook
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Вызываем правильную функцию
            success = setup_webhook() 
            if success:
                logger.error("🤖 [TELEGRAM] Вебхук успешно зарегистрирован через bot.setup_webhook().")
            else:
                logger.error("🤖 [TELEGRAM] Не удалось зарегистрировать вебхук через Телеграм API.")
        except Exception as e:
            logger.error(f"🤖 [TELEGRAM] Критическая ошибка инициализации вебхука: {e}")