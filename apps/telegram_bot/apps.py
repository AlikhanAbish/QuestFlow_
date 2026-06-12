from django.apps import AppConfig
import sys
import logging

logger = logging.getLogger(__name__)

class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telegram_bot'

    def ready(self):
        # Защищаем старт от миграций, тестов и вызовов Celery
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test', 'celery']):
            return

        # Запускаем сборку бота, чтобы проверить токены при старте основного сервера
        try:
            from .bot import get_application
            app = get_application()
            if app:
                logger.info("🤖 [TELEGRAM] Инициализация конфигурации бота в AppConfig завершена успешно.")
        except Exception as e:
            logger.error(f"🤖 [TELEGRAM] Предупреждение при инициализации приложения: {e}")