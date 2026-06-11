from django.apps import AppConfig
from django.db.models.signals import post_migrate

class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gamification'

    def ready(self):
        # Импортируем внутри метода, чтобы избежать AppRegistryNotReady
        from apps.gamification.models import GamificationRule
        import sys

        # Защита: не запускаем создание правил во время сборки, генерации миграций или тестов
        if 'makemigrations' in sys.argv or 'migrate' in sys.argv or 'test' in sys.argv:
            return

        try:
            # Проверяем, существует ли уже правило для выполнения задачи
            # get_or_create создаст его в РЕАЛЬНОЙ базе данных при старте сервера
            rule, created = GamificationRule.objects.get_or_create(
                action_type="task_done", # или как у тебя называется экшен (проверь в модели)
                defaults={
                    "xp_reward": 10, 
                    "name": "Выполнение задачи"
                }
            )
            if created:
                print("!!! ГЕЙМИФИКАЦИЯ: Правило task_done успешно создано в БД.")
        except Exception as e:
            # Если таблицы еще не созданы (первый деплой), проект не упадет
            print(f"!!! ГЕЙМИФИКАЦИЯ: Ошибка инициализации правил: {e}")


def initialize_gamification_rules(sender, **kwargs):
    """Initialize default gamification rules after migrations run."""
    try:
        from apps.gamification.models import GamificationRule
        
        default_rules = [
            {'action': 'task_done', 'xp_reward': 100},
            {'action': 'task_done_early', 'xp_reward': 150},
            {'action': 'comment', 'xp_reward': 10},
            {'action': 'daily_login', 'xp_reward': 20},
        ]

        for rule_data in default_rules:
            GamificationRule.objects.get_or_create(
                action=rule_data['action'],
                company=None,
                defaults={'xp_reward': rule_data['xp_reward'], 'is_active': True}
            )
    except Exception:
        pass
