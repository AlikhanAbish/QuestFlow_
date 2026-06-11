from django.apps import AppConfig
from django.db.models.signals import post_migrate

class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gamification'
    verbose_name = 'Gamification'

    def ready(self):
        import apps.gamification.signals
        # Initialize gamification rules after migrations
        post_migrate.connect(initialize_gamification_rules, sender=self)


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
