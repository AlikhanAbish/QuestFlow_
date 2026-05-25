from typing import Any, Optional, List

from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.gamification.engine import GamificationEngine
from apps.gamification.models import UserBadge, Badge, UserLevel, XPTransaction

User = get_user_model()

class LevelUpService:
    """Service to handle XP awards and Level Ups, wrapping GamificationEngine."""
    
    @staticmethod
    def award_xp(user, action: str, task=None, note: str = "") -> Optional[XPTransaction]:
        """
        Awards XP to a user based on action, applies streak multipliers, 
        and calculates level progression.
        """
        engine = GamificationEngine(user)
        return engine.award_xp(action=action, task=task, note=note)

    @staticmethod
    def check_level_up(user) -> bool:
        """
        Manually trigger a check for level up (usually handled inside award_xp).
        """
        engine = GamificationEngine(user)
        return engine.check_level_up()


class BadgeService:
    """Service for managing badges."""
    
    @staticmethod
    def check_and_award_badges(user, action: str) -> List[UserBadge]:
        """
        Check if any badges should be awarded for the given action.
        """
        engine = GamificationEngine(user)
        return engine.check_badges(action)
        
    @staticmethod
    def award_badge_manually(user, badge: Badge) -> Optional[UserBadge]:
        """
        Manually award a specific badge to a user if they don't have it.
        """
        ub, created = UserBadge.objects.get_or_create(user=user, badge=badge)
        if created:
            return ub
        return None


class LeaderboardService:
    """Company leaderboard — employees only (excludes admin and manager)."""

    DEFAULT_LIMIT = 10

    @classmethod
    def get_company_leaderboard(
        cls,
        *,
        company,
        current_user_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        qs = (
            UserLevel.objects.select_related("user")
            .filter(
                user__role=Role.EMPLOYEE,
                user__is_active=True,
            )
            .order_by("-total_xp")
        )
        if company is not None:
            qs = qs.filter(user__company=company)

        top_users = qs[: limit or cls.DEFAULT_LIMIT]

        return [
            {
                "rank": index + 1,
                "name": user_level.user.get_full_name() or user_level.user.email,
                "xp": user_level.total_xp,
                "is_me": user_level.user_id == current_user_id,
                "level": user_level.level,
            }
            for index, user_level in enumerate(top_users)
        ]
