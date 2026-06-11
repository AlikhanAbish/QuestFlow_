from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tasks.models import Task

from django.db import transaction
from django.db.models import Q
from apps.gamification.models import (
    GamificationRule, UserLevel, XPTransaction, UserBadge, Badge, LevelHistory
)

class GamificationEngine:
    def __init__(self, user):
        self.user = user
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        """Load gamification rules for the user's company, fallback to global."""
        # Get global rules and company rules
        company_id = self.user.company_id if hasattr(self.user, 'company_id') else None
        
        # Load rules, order by company_id so company rules overwrite global ones
        rules_qs = GamificationRule.objects.filter(
            Q(company_id=company_id) | Q(company__isnull=True),
            is_active=True
        ).order_by('company_id')
        
        rules_dict = {}
        for rule in rules_qs:
            rules_dict[rule.action] = rule
            
        return rules_dict

    def _get_streak_multiplier(self) -> float:
        """
        TZ 2.1.3: +10% XP bonus for each consecutive streak day.
        Max bonus is +30% (achieved at streak >= 3 days).
        """
        if not hasattr(self.user, 'streak'):
            return 1.0
        streak = self.user.streak.current
        # +10% per day, capped at +30% (streak >= 3)
        return 1.0 + (min(streak, 3) * 0.10)

    @transaction.atomic
    def handle_login(self):
        """
        Logic to execute on user login:
        1. Update streak (increment or reset).
        2. Award daily login XP.
        """
        from django.utils import timezone
        from apps.gamification.models import Streak
        
        streak, _ = Streak.objects.get_or_create(user=self.user)
        today = timezone.now().date()
        
        if streak.last_active:
            delta = (today - streak.last_active).days
            if delta == 1:
                # Logged in consecutive day
                streak.current += 1
                if streak.current > streak.longest:
                    streak.longest = streak.current
            elif delta > 1:
                # Missed day(s), reset streak
                streak.current = 1
            # If delta == 0, already logged in today, do nothing to streak
        else:
            # First time activity
            streak.current = 1
            streak.longest = 1
            
        if not streak.last_active or streak.last_active < today:
            streak.last_active = today
            streak.save()
            
            # Award daily login XP
            self.award_xp(action='daily_login', note="Daily login bonus")

    @transaction.atomic
    def award_xp(self, action: str, task: "Optional[Task]" = None, note: str = "") -> tuple[Optional[XPTransaction], bool]:
        """Award XP for action, apply streak multiplier, check level-up."""
        from apps.gamification.models import GamificationRule
        
        rule = self.rules.get(action)
        
        # Исправляем action_type на action
        if not rule:
            rule, created = GamificationRule.objects.get_or_create(
                action=action,  # ТУТ БЫЛО action_type, СТАЛО action
                defaults={
                    "xp_reward": 10,
                    # Если в модели нет поля name, убираем его, 
                    # судя по choices поля name там тоже нет, так что оставляем только xp_reward
                }
            )
            if hasattr(self, 'rules') and isinstance(self.rules, dict):
                self.rules[action] = rule

        if not rule:
            return None, False

        base_xp = rule.xp_reward
        # ... дальше твой оригинальный код без изменений ...
        multiplier = self._get_streak_multiplier()
        final_xp = int(base_xp * multiplier)

        txn = XPTransaction.objects.create(
            user=self.user,
            amount=final_xp,
            action=action,
            related_task=task,
            note=note
        )

        self._update_user_xp(final_xp)
        leveled_up = self.check_level_up()
        self.check_badges(action)

        return txn, leveled_up

    def _update_user_xp(self, amount: int):
        level_data, _ = UserLevel.objects.get_or_create(user=self.user)
        level_data.total_xp += amount
        level_data.weekly_xp += amount
        level_data.save(update_fields=['total_xp', 'weekly_xp'])

    @transaction.atomic
    def check_level_up(self) -> bool:
        """Return True if user leveled up after XP award."""
        level_data, _ = UserLevel.objects.get_or_create(user=self.user)
        current_level = level_data.level
        new_level = current_level
        leveled_up = False

        while True:
            # XP threshold formula: 500 * L * (L+1) // 2 (TZ 2.1.3)
            next_level_xp = 500 * new_level * (new_level + 1) // 2
            if level_data.total_xp >= next_level_xp:
                new_level += 1
                leveled_up = True
            else:
                break

        if leveled_up:
            level_data.level = new_level
            level_data.save(update_fields=['level'])

            # Create history record
            LevelHistory.objects.create(
                user=self.user,
                level=new_level,
                total_xp=level_data.total_xp
            )

            MILESTONE_LEVELS = {10, 20, 30, 40, 50}
            try:
                from apps.notifications.services import NotificationService

                NotificationService.notify_level_up(self.user, new_level)
                if new_level in MILESTONE_LEVELS:
                    NotificationService.notify_employee_milestone(self.user, new_level)
            except Exception:
                pass

            if new_level in MILESTONE_LEVELS:
                self._notify_telegram_milestone(new_level)

            # TZ 6.6: Send Telegram notification
            self._notify_telegram_level_up(new_level)

        return leveled_up

    def _notify_telegram_milestone(self, milestone_level: int) -> None:
        """TZ 6.6: Telegram alert to managers/admins on employee milestone."""
        from apps.accounts.models import Role

        if self.user.role != Role.EMPLOYEE:
            return
        try:
            from apps.telegram_bot.tasks import send_milestone_notification
            send_milestone_notification.delay(self.user.id, milestone_level)
        except Exception:
            pass

    @transaction.atomic
    def check_badges(self, action: str) -> List[UserBadge]:
        """Evaluate all badge triggers and award if criteria met."""
        awarded_badges = []
        
        # Get active badges matching this trigger
        potential_badges = Badge.objects.filter(is_active=True, trigger=action)
        
        # Exclude badges the user already has
        user_badge_ids = UserBadge.objects.filter(user=self.user).values_list('badge_id', flat=True)
        potential_badges = potential_badges.exclude(id__in=user_badge_ids)
        
        for badge in potential_badges:
            # Evaluate trigger logic based on trigger_value JSON
            if self._evaluate_badge_trigger(badge):
                ub = UserBadge.objects.create(user=self.user, badge=badge)
                awarded_badges.append(ub)
                
                # TZ 6.6: Send Telegram notification for each badge
                self._notify_telegram_badge(badge.id)
                
        return awarded_badges
        
    def _evaluate_badge_trigger(self, badge: Badge) -> bool:
        """Evaluate logic for specific badges based on trigger and trigger_value."""
        trigger_value = badge.trigger_value or {}
        
        # Simple count-based triggers (e.g. 7 days streak)
        if badge.trigger == 'streak_days':
            target_days = trigger_value.get('count', 0)
            if hasattr(self.user, 'streak') and self.user.streak.longest >= target_days:
                return True
                
        # First task completed
        if badge.trigger == 'first_task':
            # This logic assumes the action was 'task_done' and we just check if any exists
            count = XPTransaction.objects.filter(user=self.user, action__in=['task_done', 'task_done_early']).count()
            if count >= trigger_value.get('count', 1):
                return True
                
        # Add more trigger logic here as needed
        return False

    def _notify_telegram_level_up(self, new_level: int) -> None:
        """
        TZ 6.6: Send Telegram notification when an employee levels up.
        Managers/admins do not receive personal level-up messages.
        """
        from apps.accounts.models import Role

        if self.user.role != Role.EMPLOYEE:
            return
        try:
            from apps.telegram_bot.tasks import send_level_up_notification
            send_level_up_notification.delay(self.user.id, new_level)
        except Exception:
            # Telegram notification is non-critical
            pass

    def _notify_telegram_badge(self, badge_id: int) -> None:
        """
        TZ 6.6: Send Telegram notification when user earns a badge.
        Non-blocking — never breaks the main flow if Telegram is unavailable.
        """
        try:
            from apps.telegram_bot.tasks import send_badge_notification
            send_badge_notification.delay(self.user.id, badge_id)
        except Exception:
            # Telegram notification is non-critical
            pass
