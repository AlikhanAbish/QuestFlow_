from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class GamificationRule(TimeStampedModel):
    company = models.ForeignKey(
        'companies.Company', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="If null, this is a global rule"
    )
    action = models.CharField(max_length=100)
    xp_reward = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        scope = self.company.name if self.company else "Global"
        return f"{self.action} ({scope}): {self.xp_reward} XP"

class UserLevel(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='level_data')
    level = models.PositiveIntegerField(default=1)
    total_xp = models.PositiveIntegerField(default=0)
    weekly_xp = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} - Level {self.level} ({self.total_xp} XP)"

class XPTransaction(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_transactions')
    amount = models.IntegerField()
    action = models.CharField(max_length=100)
    related_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user} {'+' if self.amount >= 0 else ''}{self.amount} XP ({self.action})"

class Streak(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='streak')
    current = models.PositiveIntegerField(default=0)
    longest = models.PositiveIntegerField(default=0)
    last_active = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.current} days"

class Badge(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)
    trigger = models.CharField(max_length=100)
    trigger_value = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class UserBadge(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['user', 'badge']]

    def __str__(self):
        return f"{self.user} - {self.badge.name}"

class RewardType(models.TextChoices):
    CERTIFICATE = 'certificate', 'Certificate'
    BONUS = 'bonus', 'Bonus'
    DAY_OFF = 'day_off', 'Day Off'
    CUSTOM = 'custom', 'Custom'

class RealReward(TimeStampedModel):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rewards')
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='granted_rewards')
    reward_type = models.CharField(max_length=50, choices=RewardType.choices)
    description = models.TextField()
    milestone_level = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.reward_type} to {self.recipient.email} (Lvl {self.milestone_level})"

class LevelHistory(TimeStampedModel):
    """Optional model to track when users level up for analytics and timelines."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='level_history')
    level = models.PositiveIntegerField()
    total_xp = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.user} leveled up to {self.level}"
