"""
NotificationService — TZ sections 2.1.5, 4.8, 5.7, 6.6.

All business logic for creating, sending, and managing notifications
lives here. Views and signals call this service.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.accounts.models import Role

from .models import (
    FILTER_BURNOUT_TYPES,
    FILTER_GAMIFICATION_TYPES,
    FILTER_TASK_TYPES,
    TEAM_SCOPED_TYPES,
    Notification,
    NotificationScope,
    NotificationTemplate,
    NotificationType,
)

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
        *,
        scope: str = NotificationScope.PERSONAL,
    ) -> Notification:
        """
        Low-level factory: create and persist one Notification.
        """
        meta = dict(metadata or {})
        meta.setdefault('scope', scope)

        notification = Notification.objects.create(
            recipient=recipient,
            type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            metadata=meta,
        )
        logger.info(
            "Notification created: type=%s scope=%s recipient=%s",
            notification_type,
            scope,
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

    # --- Shortcut senders (personal) ----------------------------------------

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
            scope=NotificationScope.PERSONAL,
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
            scope=NotificationScope.PERSONAL,
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
            scope=NotificationScope.PERSONAL,
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
            scope=NotificationScope.PERSONAL,
        )

    @classmethod
    def notify_assessment_due(cls, recipient: 'User') -> Notification:
        return cls.create_notification(
            recipient=recipient,
            notification_type=NotificationType.ASSESSMENT_DUE,
            title='📝 Weekly Assessment Due',
            body='Your weekly burnout self-assessment is ready. It only takes 2 minutes.',
            action_url='/burnout/',
            scope=NotificationScope.PERSONAL,
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
            scope=NotificationScope.PERSONAL,
        )

    # --- Shortcut senders (team / manager) ----------------------------------

    @classmethod
    def notify_employee_milestone(cls, employee: 'User', milestone_level: int) -> list[Notification]:
        """Notify managers/admins when an employee reaches a milestone level."""
        from django.urls import reverse

        from apps.telegram_bot.notifications import get_employee_alert_recipients

        employee_name = employee.get_full_name() or employee.email
        created: list[Notification] = []
        for recipient in get_employee_alert_recipients(employee):
            created.append(cls.create_notification(
                recipient=recipient,
                notification_type=NotificationType.ACHIEVEMENT,
                title=f'🏆 {employee_name} reached Level {milestone_level}!',
                body=(
                    f'{employee_name} has reached Level {milestone_level} — a milestone achievement! '
                    f'Consider granting them a real-world reward in QuestFlow.'
                ),
                action_url=reverse('gamification:profile', args=[employee.pk]),
                metadata={
                    'milestone_level': milestone_level,
                    'employee_id': employee.pk,
                },
                scope=NotificationScope.TEAM,
            ))
        return created

    @classmethod
    def notify_task_completed_team(cls, task, completed_by: 'User | None' = None) -> list[Notification]:
        """Notify managers/admins when an employee completes a task."""
        from django.urls import reverse

        from apps.telegram_bot.notifications import get_employee_alert_recipients

        assignee = task.assigned_to
        if not assignee or assignee.role != Role.EMPLOYEE:
            return []

        assignee_name = assignee.get_full_name() or assignee.email
        team_name = task.team.name if getattr(task, 'team', None) else '—'
        body = f'{assignee_name} completed "{task.title}" (Team: {team_name}).'
        if completed_by and completed_by.pk != assignee.pk:
            marker = completed_by.get_full_name() or completed_by.email
            body += f' Marked done by {marker}.'

        created: list[Notification] = []
        for recipient in get_employee_alert_recipients(assignee):
            created.append(cls.create_notification(
                recipient=recipient,
                notification_type=NotificationType.TASK_COMPLETED,
                title=f'✅ Task completed by {assignee_name}',
                body=body,
                action_url=reverse('tasks:task_detail', args=[task.pk]),
                metadata={'task_id': task.pk, 'employee_id': assignee.pk},
                scope=NotificationScope.TEAM,
            ))
        return created

    @classmethod
    def notify_team_burnout_change(
        cls,
        team,
        employee: 'User',
        old_level: str,
        new_level: str,
        summary: dict,
    ) -> list[Notification]:
        """Notify managers/admins when team burnout distribution changes."""
        from django.urls import reverse

        from apps.telegram_bot.notifications import get_team_notification_recipients

        employee_name = employee.get_full_name() or employee.email
        level_labels = {'green': 'Healthy', 'yellow': 'At Risk', 'red': 'Burned Out'}
        old_label = level_labels.get(old_level, old_level)
        new_label = level_labels.get(new_level, new_level)
        total = summary.get('total', 0)

        body = (
            f'{employee_name}: {old_label} → {new_label}. '
            f'Team distribution ({total} members): '
            f'🟢 {summary.get("green", 0)} · '
            f'🟡 {summary.get("yellow", 0)} · '
            f'🔴 {summary.get("red", 0)}'
        )

        created: list[Notification] = []
        for recipient in get_team_notification_recipients(team):
            created.append(cls.create_notification(
                recipient=recipient,
                notification_type=NotificationType.BURNOUT_CHANGE,
                title=f'📊 Team burnout updated — {team.name}',
                body=body,
                action_url=reverse('burnout:team_summary'),
                metadata={
                    'employee_id': employee.pk,
                    'team_id': team.pk,
                    'old_level': old_level,
                    'new_level': new_level,
                },
                scope=NotificationScope.TEAM,
            ))
        return created

    # --- Read management ----------------------------------------------------

    @staticmethod
    def mark_as_read(notification_id: int, user: 'User') -> bool:
        """
        Mark a single notification as read. Returns True on success.
        Silently ignores if the notification doesn't belong to the user.
        """
        qs = NotificationService._visible_queryset(user)
        updated = qs.filter(pk=notification_id, is_read=False).update(is_read=True)
        return bool(updated)

    @staticmethod
    def mark_all_as_read(user: 'User', *, scope: str | None = None) -> int:
        """Mark unread notifications as read. Optional scope limits the batch."""
        qs = NotificationService._visible_queryset(user).filter(is_read=False)
        if scope in (NotificationScope.PERSONAL, NotificationScope.TEAM):
            qs = NotificationService._apply_scope_filter(qs, scope)
        return qs.update(is_read=True)

    # --- Query helpers ------------------------------------------------------

    @staticmethod
    def is_manager_or_admin(user: 'User') -> bool:
        return user.role in (Role.MANAGER, Role.ADMIN)

    @classmethod
    def _visible_queryset(cls, user: 'User') -> QuerySet:
        """
        Base queryset for a user.
        Employees only see personal notifications; managers/admins see all theirs.
        """
        qs = Notification.objects.filter(recipient=user)
        if cls.is_manager_or_admin(user):
            return qs
        return qs.filter(
            Q(metadata__scope=NotificationScope.PERSONAL)
            | (
                ~Q(metadata__scope=NotificationScope.TEAM)
                & ~Q(
                    type__in=TEAM_SCOPED_TYPES,
                    metadata__employee_id__isnull=False,
                )
            )
        )

    @staticmethod
    def _apply_scope_filter(qs: QuerySet, scope: str) -> QuerySet:
        if scope == NotificationScope.TEAM:
            return qs.filter(
                Q(metadata__scope=NotificationScope.TEAM)
                | Q(type__in=TEAM_SCOPED_TYPES, metadata__employee_id__isnull=False)
            )
        if scope == NotificationScope.PERSONAL:
            return qs.filter(
                Q(metadata__scope=NotificationScope.PERSONAL)
                | (
                    ~Q(metadata__scope=NotificationScope.TEAM)
                    & ~Q(
                        type__in=TEAM_SCOPED_TYPES,
                        metadata__employee_id__isnull=False,
                    )
                )
            )
        return qs

    @classmethod
    def _apply_category_filter(cls, qs: QuerySet, filter_key: str) -> QuerySet:
        if filter_key == 'unread':
            return qs.filter(is_read=False)
        if filter_key == 'tasks':
            return qs.filter(type__in=FILTER_TASK_TYPES)
        if filter_key == 'gamification':
            return qs.filter(type__in=FILTER_GAMIFICATION_TYPES)
        if filter_key == 'burnout':
            return qs.filter(type__in=FILTER_BURNOUT_TYPES)
        return qs

    @classmethod
    def get_for_user(
        cls,
        user: 'User',
        *,
        filter_key: str = 'all',
        scope: str | None = None,
    ) -> QuerySet:
        qs = cls._visible_queryset(user).order_by('-created_at')
        if scope in (NotificationScope.PERSONAL, NotificationScope.TEAM):
            qs = cls._apply_scope_filter(qs, scope)
        if filter_key and filter_key != 'all':
            qs = cls._apply_category_filter(qs, filter_key)
        return qs

    @staticmethod
    def get_unread_count(user: 'User', *, scope: str | None = None) -> int:
        qs = NotificationService._visible_queryset(user).filter(is_read=False)
        if scope in (NotificationScope.PERSONAL, NotificationScope.TEAM):
            qs = NotificationService._apply_scope_filter(qs, scope)
        return qs.count()

    @staticmethod
    def get_recent(user: 'User', limit: int = 8) -> QuerySet:
        return NotificationService.get_for_user(user)[:limit]

    @staticmethod
    def get_all_for_user(
        user: 'User',
        *,
        filter_key: str = 'all',
        scope: str | None = None,
    ) -> QuerySet:
        return NotificationService.get_for_user(
            user,
            filter_key=filter_key,
            scope=scope,
        )

    @staticmethod
    def get_notification_for_user(user: 'User', notification_id: int) -> Notification | None:
        return NotificationService._visible_queryset(user).filter(pk=notification_id).first()
