from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    # Dashboard partials
    path('dashboard/xp-counter/', views.XPCounterPartialView.as_view(), name='xp-counter'),
    path('dashboard/leaderboard/', views.LeaderboardPartialView.as_view(), name='leaderboard'),
    
    # Profile & Badges
    path('profile/<int:user_id>/', views.UserProfileGamificationView.as_view(), name='profile'),
    path('badges/', views.BadgesPartialView.as_view(), name='badges'),
]
