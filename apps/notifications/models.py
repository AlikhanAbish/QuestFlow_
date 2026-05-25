from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class NotificationType(models.TextChoices):
    TASK_ASSIGNED   = 'task_assigned',   'Task Assigned'
    TASK_COMPLETED  = 'task_completed',  'Task Completed'
    TASK_OVERDUE    = 'task_overdue',    'Task Overdue'
    NEW_TASK        = 'new_task',        'New Task'
    LEVEL_UP        = 'level_up',        'Level Up'
    BADGE_EARNED    = 'badge_earned',    'Badge Earned'
    MILESTONE_REWARD = 'milestone_reward', 'Milestone Reward'
    BURNOUT_CHANGE  = 'burnout_change',  'Burnout Change'
    BURNOUT_ALERT   = 'burnout_alert',   'Burnout Alert'
    ASSESSMENT_DUE  = 'assessment_due',  'Assessment Due'
    ACHIEVEMENT     = 'achievement',     'Achievement'
    REWARD          = 'reward',          'Reward'
    STREAK_UPDATE   = 'streak_update',   'Streak Update'
    SYSTEM          = 'system',          'System'


# Icon map — used in templates to display per-type icons
NOTIFICATION_ICONS = {
    NotificationType.TASK_ASSIGNED:   '📋',
    NotificationType.TASK_COMPLETED:  '✅',
    NotificationType.TASK_OVERDUE:    '⚠️',
    NotificationType.NEW_TASK:        '📌',
    NotificationType.LEVEL_UP:        '🚀',
    NotificationType.BADGE_EARNED:    '🏅',
    NotificationType.MILESTONE_REWARD: '🎁',
    NotificationType.BURNOUT_CHANGE:  '📊',
    NotificationType.BURNOUT_ALERT:   '🔥',
    NotificationType.ASSESSMENT_DUE:  '📝',
    NotificationType.ACHIEVEMENT:     '⭐',
    NotificationType.REWARD:          '🎉',
    NotificationType.STREAK_UPDATE:   '🔥',
    NotificationType.SYSTEM:          'ℹ️',
}

# Color map — Tailwind bg color classes per type
NOTIFICATION_COLORS = {
    NotificationType.TASK_ASSIGNED:   'bg-blue-500/20 text-blue-400',
    NotificationType.TASK_COMPLETED:  'bg-green-500/20 text-green-400',
    NotificationType.TASK_OVERDUE:    'bg-red-500/20 text-red-400',
    NotificationType.NEW_TASK:        'bg-indigo-500/20 text-indigo-400',
    NotificationType.LEVEL_UP:        'bg-purple-500/20 text-purple-400',
    NotificationType.BADGE_EARNED:    'bg-amber-500/20 text-amber-400',
    NotificationType.MILESTONE_REWARD: 'bg-amber-500/20 text-amber-400',
    NotificationType.BURNOUT_CHANGE:  'bg-orange-500/20 text-orange-400',
    NotificationType.BURNOUT_ALERT:   'bg-red-500/20 text-red-400',
    NotificationType.ASSESSMENT_DUE:  'bg-yellow-500/20 text-yellow-400',
    NotificationType.ACHIEVEMENT:     'bg-yellow-500/20 text-yellow-400',
    NotificationType.REWARD:          'bg-pink-500/20 text-pink-400',
    NotificationType.STREAK_UPDATE:   'bg-orange-500/20 text-orange-400',
    NotificationType.SYSTEM:          'bg-zinc-500/20 text-zinc-400',
}


class Notification(TimeStampedModel):
    """
    TZ 2.1.5 / 5.7: In-app notification model.
    Used for bell-icon dropdown and milestone alerts.
    """
    recipient  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type       = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True,
    )
    title      = models.CharField(max_length=255)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(max_length=500, blank=True)
    metadata   = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self) -> str:
        return f"[{self.type}] → {self.recipient.email}: {self.title}"

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    @property
    def icon(self) -> str:
        return NOTIFICATION_ICONS.get(self.type, 'ℹ️')

    @property
    def color_class(self) -> str:
        return NOTIFICATION_COLORS.get(self.type, 'bg-zinc-500/20 text-zinc-400')


class NotificationTemplate(TimeStampedModel):
    """
    TZ 4.8 / 6.6: Reusable templates for generating notifications.
    Services use these templates to create consistent messages.
    """
    name             = models.CharField(max_length=100, unique=True)
    type             = models.CharField(max_length=50, choices=NotificationType.choices)
    title_template   = models.CharField(
        max_length=255,
        help_text="Use {variable} placeholders, e.g. 'New task: {task_title}'",
    )
    body_template    = models.TextField(
        help_text="Use {variable} placeholders for the notification body.",
    )
    default_action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional URL pattern with {variable} placeholders.",
    )
    is_active        = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"

    def render(self, context: dict) -> tuple[str, str, str]:
        """
        Render title, body and action_url with the given context dict.
        Returns (title, body, action_url).
        """
        title      = self.title_template.format(**context)
        body       = self.body_template.format(**context)
        action_url = self.default_action_url.format(**context) if self.default_action_url else ''
        return title, body, action_url
