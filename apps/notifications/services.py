"""
NotificationService — TZ sections 2.1.5, 4.8, 5.7, 6.6.

All business logic for creating, sending, and managing notifications
lives here. Views and signals call this service.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import QuerySet

from .models import Notification, NotificationTemplate, NotificationType

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    User = get_user_model()

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service layer for all notification operations.
    """

    # --- Creation helpers ---------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_notification(
        recipient: 'User',
        notification_type: str,
        title: str,
        body: str,
        action_url: str = '',
        metadata: dict | None = None,
    ) -> Notification:
        """
        Low-level factory: create and persist one Notification.
        """
        notification = Notification.objects.create(
            recipient=recipient,
            type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            metadata=metadata or {},
        )
        logger.info(
            "Notification created: type=%s recipient=%s",
            notification_type,
            recipient.pk,
        )
        return notification

    @classmethod
    def send_notification(
        cls,
        recipient: 'User',
        template_name: str,
        context: dict,
        metadata: dict | None = None,
    ) -> Notification | None:
        """
        High-level factory: look up a NotificationTemplate by name,
        render it with *context*, then persist the notification.
        Returns None (and logs a warning) if the template doesn't exist or is inactive.
        """
        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
        except NotificationTemplate.DoesNotExist:
            logger.warning("NotificationTemplate '%s' not found or inactive.", template_name)
            return None

        title, body, action_url = template.render(context)
        return cls.create_notification(
            recipient=recipient,
            notification_type=template.type,
            title=title,
            body=body,
            action_url=action_url,
            metadata=metadata or {},
        )

    # --- Shortcut senders ---------------------------------------------------

    @classmethod
    def notify_task_assigned(cls, recipient: 'User', task) -> Notification:
        from django.urls import reverse
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.TASK_ASSIGNED,
            title='New task assigned to you',
            body=f'You have been assigned to "{task.title}".',
            action_url=reverse('tasks:task_detail', args=[task.pk]),
            metadata={'task_id': task.pk},
        )

    @classmethod
    def notify_level_up(cls, recipient: 'User', new_level: int) -> Notification:
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.LEVEL_UP,
            title=f'🚀 Level Up! You reached Level {new_level}',
            body='Keep completing tasks and maintaining your streak to climb higher!',
            action_url='/gamification/profile/',
            metadata={'new_level': new_level},
        )

    @classmethod
    def notify_badge_earned(cls, recipient: 'User', badge_name: str) -> Notification:
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.BADGE_EARNED,
            title=f'🏅 Badge Earned: {badge_name}',
            body=f'You unlocked the "{badge_name}" badge. Great work!',
            action_url='/gamification/profile/',
            metadata={'badge_name': badge_name},
        )

    @classmethod
    def notify_burnout_alert(cls, recipient: 'User', score: str) -> Notification:
        labels = {'red': 'High burnout risk detected', 'yellow': 'Moderate stress detected'}
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.BURNOUT_ALERT,
            title=labels.get(score, 'Burnout assessment update'),
            body='Your latest burnout assessment requires attention. Please review your workload.',
            action_url='/burnout/',
            metadata={'score': score},
        )

    @classmethod
    def notify_assessment_due(cls, recipient: 'User') -> Notification:
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.ASSESSMENT_DUE,
            title='📝 Weekly Assessment Due',
            body='Your weekly burnout self-assessment is ready. It only takes 2 minutes.',
            action_url='/burnout/',
        )

    @classmethod
    def notify_milestone_reward(cls, recipient: 'User', reward_name: str) -> Notification:
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.MILESTONE_REWARD,
            title=f'🎁 Reward Unlocked: {reward_name}',
            body=f'You earned a milestone reward: "{reward_name}". Keep up the great work!',
            action_url='/gamification/profile/',
            metadata={'reward_name': reward_name},
        )

    # --- Read management ----------------------------------------------------

    @staticmethod
    def mark_as_read(notification_id: int, user: 'User') -> bool:
        """
        Mark a single notification as read. Returns True on success.
        Silently ignores if the notification doesn't belong to the user.
        """
        updated = Notification.objects.filter(
            pk=notification_id,
            recipient=user,
            is_read=False,
        ).update(is_read=True)
        return bool(updated)

    @staticmethod
    def mark_all_as_read(user: 'User') -> int:
        """Mark all unread notifications for user as read. Returns count updated."""
        return Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)

    # --- Query helpers ------------------------------------------------------

    @staticmethod
    def get_unread_count(user: 'User') -> int:
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def get_recent(user: 'User', limit: int = 8) -> QuerySet:
        return Notification.objects.filter(recipient=user).order_by('-created_at')[:limit]

    @staticmethod
    def get_all_for_user(user: 'User') -> QuerySet:
        return Notification.objects.filter(recipient=user).order_by('-created_at')
