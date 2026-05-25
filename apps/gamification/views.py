from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from apps.core.mixins import HtmxTemplateResponseMixin
from apps.accounts.mixins import RoleRequiredMixin
from apps.gamification.models import UserLevel, XPTransaction, UserBadge
from apps.gamification.services import LeaderboardService

User = get_user_model()

class XPCounterPartialView(LoginRequiredMixin, HtmxTemplateResponseMixin, TemplateView):
    template_name = 'dashboard/partials/_xp_counter.html'
    htmx_template_name = 'dashboard/partials/_xp_counter.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_level, _ = UserLevel.objects.get_or_create(user=self.request.user)
        
        current_level = user_level.level
        xp_total = user_level.total_xp
        
        # Calculate XP needed for next level: 500 * L * (L+1) // 2
        xp_next_level = 500 * current_level * (current_level + 1) // 2
        # Calculate base XP for current level to find the progress range
        xp_current_level_base = 500 * (current_level - 1) * current_level // 2 if current_level > 1 else 0
        
        xp_in_level = xp_total - xp_current_level_base
        xp_required_for_level = xp_next_level - xp_current_level_base
        progress_percent = int((xp_in_level / xp_required_for_level) * 100) if xp_required_for_level > 0 else 0
        
        # Check if leveled up recently (e.g. in the last minute)
        # Using the session or a simple DB query on LevelHistory might be better, 
        # but let's assume we can trigger the animation via Alpine.js on XP increase
        
        streak_obj = getattr(self.request.user, 'streak', None)
        streak_days = streak_obj.current if streak_obj else 0
        
        # Check if leveled up in the last 10 seconds
        has_recent_levelup = False
        from apps.gamification.models import LevelHistory
        recent_level = LevelHistory.objects.filter(
            user=self.request.user, 
            created_at__gte=timezone.now() - timedelta(seconds=10)
        ).first()
        if recent_level:
            has_recent_levelup = True

        ctx.update({
            'level': current_level,
            'xp_total': xp_total,
            'xp_next_level': xp_next_level,
            'xp_weekly': user_level.weekly_xp,
            'streak': streak_days,
            'progress_percent': min(progress_percent, 100),
            'has_recent_levelup': has_recent_levelup
        })
            
        return ctx

class LeaderboardPartialView(LoginRequiredMixin, HtmxTemplateResponseMixin, TemplateView):
    template_name = 'dashboard/partials/_leaderboard.html'
    htmx_template_name = 'dashboard/partials/_leaderboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leaderboard"] = LeaderboardService.get_company_leaderboard(
            company=getattr(self.request.user, "company", None),
            current_user_id=self.request.user.id,
        )
        return ctx

class UserProfileGamificationView(LoginRequiredMixin, HtmxTemplateResponseMixin, DetailView):
    model = User
    template_name = 'gamification/profile.html'
    htmx_template_name = 'gamification/partials/_profile_content.html'
    context_object_name = 'profile_user'
    pk_url_kwarg = 'user_id'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        user_level, _ = UserLevel.objects.get_or_create(user=profile_user)
        
        ctx['user_level'] = user_level
        # Recent XP transactions
        ctx['recent_transactions'] = XPTransaction.objects.filter(user=profile_user).order_by('-created_at')[:10]
        ctx['badges'] = UserBadge.objects.filter(user=profile_user).select_related('badge').order_by('-awarded_at')
        return ctx

class BadgesPartialView(LoginRequiredMixin, HtmxTemplateResponseMixin, TemplateView):
    template_name = 'gamification/partials/_badges.html'
    htmx_template_name = 'gamification/partials/_badges.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['badges'] = UserBadge.objects.filter(user=self.request.user).select_related('badge').order_by('-awarded_at')
        return ctx
