"""
NotificationService — TZ sections 2.1.5, 4.8, 5.7, 6.6.

All business logic for creating, sending, and managing notifications
lives here. Views and signals call this service.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

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


# ============================================================================
# Email Service (Brevo API)
# ============================================================================


class BrevoEmailError(Exception):
    """Raised when Brevo API email delivery fails."""


class BrevoEmailService:
    """
    Send emails via Brevo HTTP API instead of SMTP.
    
    **Why Brevo API instead of SMTP?**
    - More reliable than SMTP on Railway (no socket.gaierror/DNS failures)
    - HTTP API has better retry logic and status tracking
    - No need to manage SMTP connections
    - Proper rate limiting and error codes
    
    **Configuration:**
    - Set BREVO_API_KEY in .env: https://app.brevo.com/settings/account/api
    - Set DEFAULT_FROM_EMAIL to a verified sender (not SMTP login)
      Example: "QuestFlow <noreply@your-domain.com>"
    - In development, set EMAIL_BACKEND to console backend for testing
    
    **Usage:**
        service = BrevoEmailService()
        service.send_email(
            subject='Welcome',
            body_html='<p>Hello</p>',
            to_email='user@example.com',
            from_email='noreply@company.com',
        )
    """
    
    # Brevo SMTP Email API endpoint (HTTP, not SMTP)
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    REQUEST_TIMEOUT = 10
    
    def __init__(self):
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        # Check if using console backend (development/testing only)
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        self.use_console = 'console' in email_backend.lower()
        
        if not self.use_console and not self.api_key:
            raise BrevoEmailError(
                _("BREVO_API_KEY is not configured. Set it in .env or Django settings. "
                  "Get it from: https://app.brevo.com/settings/account/api")
            )
    
    def send_email(
        self,
        *,
        subject: str,
        body_html: str,
        to_email: str,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send email via Brevo API (or console backend in development).
        
        Args:
            subject: Email subject line
            body_html: HTML email body
            to_email: Recipient email address
            from_email: Sender email (uses DEFAULT_FROM_EMAIL if None)
        
        Returns:
            True if sent successfully
        
        Raises:
            BrevoEmailError: If sending fails
        """
        # Use configured default sender if not provided
        if not from_email:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
            if not from_email:
                raise BrevoEmailError(
                    _("DEFAULT_FROM_EMAIL is not configured.")
                )
        
        # Development: use console backend
        if self.use_console:
            logger.info(
                "Console backend: email to=%s from=%s subject=%r",
                to_email, from_email, subject,
            )
            return True
        
        # Production: send via Brevo API
        return self._send_via_api(
            subject=subject,
            body_html=body_html,
            to_email=to_email,
            from_email=from_email,
        )
    
    
    def _send_via_api(self, to_email, subject, html_content):
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        # 1. Настройка конфигурации авторизации
        configuration = sib_api_v3_sdk.Configuration()
        # Очищаем ключ от любых фантомных символов переноса строки
        configuration.api_key['api-key'] = str(self.api_key).strip().replace("\n", "").replace("\r", "")

        # 2. Инициализация официального клиента API
        api_client = sib_api_v3_sdk.ApiClient(configuration)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        # 3. Сборка объекта письма строго по спецификации SDK
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "QuestFlow", "email": "invite@questflow.online"},
            to=[{"email": to_email}],
            subject=subject,
            html_content=html_content
        )

        try:
            # Отправка через встроенный метод библиотеки
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info("!!! BREVO SDK SUCCESS: %s", api_response)
            return True
        except ApiException as e:
            # Если Brevo вернет ошибку, SDK выведет её структурированно
            logger.error("!!! КРИТИЧЕСКАЯ ОШИБКА BREVO SDK: Status=%s | Body=%s", e.status, e.body)
            raise BrevoEmailError(f"Email service error via SDK: {e.body}")        
        except BrevoEmailError:
            # Пробрасываем наши кастомные ошибки выше без изменений
            raise
        except requests.exceptions.Timeout:
            logger.exception("Brevo API timeout: to=%s", to_email)
            raise BrevoEmailError(_("Email service request timed out."))
        except requests.exceptions.RequestException as exc:
            logger.exception("Brevo API request failed: to=%s", to_email)
            raise BrevoEmailError(_("Could not reach email service.")) from exc
        except Exception as exc:
            logger.exception("Unexpected error sending email to=%s", to_email)
            raise BrevoEmailError(_("Could not send email.")) from exc

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
