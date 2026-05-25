from django.core.management.base import BaseCommand
from apps.gamification.models import GamificationRule

class Command(BaseCommand):
    help = 'Seed default gamification rules'

    def handle(self, *args, **options):
        rules = [
            {'action': 'task_done', 'xp_reward': 100},
            {'action': 'task_done_early', 'xp_reward': 150},
            {'action': 'comment', 'xp_reward': 10},
            {'action': 'daily_login', 'xp_reward': 20},
        ]

        for rule_data in rules:
            rule, created = GamificationRule.objects.get_or_create(
                action=rule_data['action'],
                company=None,  # Global rule
                defaults={'xp_reward': rule_data['xp_reward']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created global rule: {rule_data['action']}"))
            else:
                rule.xp_reward = rule_data['xp_reward']
                rule.save()
                self.stdout.write(self.style.SUCCESS(f"Updated global rule: {rule_data['action']}"))
