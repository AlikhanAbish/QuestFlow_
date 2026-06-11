import logging

from django.utils import timezone
from django.db import transaction
from typing import Any, Dict, List, Optional
from django.db.models import QuerySet

from .models import Task, Comment, TaskHistory, TaskStatus
from .signals import task_completed
from apps.companies.models import Company
from apps.accounts.models import User
from apps.gamification.engine import GamificationEngine

logger = logging.getLogger(__name__)


class TaskService:
    """Service class encapsulating business logic for Task management."""

    @staticmethod
    def _create_history(task: Task, changed_by: User, field_name: str, old_value: Any, new_value: Any) -> None:
        """Helper method to create a TaskHistory entry."""
        if str(old_value) != str(new_value):
            TaskHistory.objects.create(
                task=task,
                changed_by=changed_by,
                field_name=field_name,
                old_value=str(old_value),
                new_value=str(new_value)
            )

    @classmethod
    @transaction.atomic
    def create_task(cls, company: Company, created_by: User, **kwargs: Any) -> Task:
        """Create a new task and record its creation."""
        task = Task.objects.create(
            company=company,
            created_by=created_by,
            **kwargs
        )
        # Create history record for creation
        cls._create_history(task, created_by, 'status', '', task.status)
        
        # TZ 6.6: Send Telegram notification if task is assigned to someone
        if task.assigned_to:
            cls._notify_task_assigned(task)
        
        return task

    @classmethod
    @transaction.atomic
    def update_task(cls, task: Task, changed_by: User, **kwargs: Any) -> Task:
        """Update a task and record history for changed fields."""
        # Get old values
        old_values = {key: getattr(task, key) for key in kwargs.keys()}

        # Update fields
        for key, value in kwargs.items():
            setattr(task, key, value)
        
        task.save(update_fields=kwargs.keys())

        # Create history records
        for key, new_value in kwargs.items():
            old_value = old_values[key]
            # Handle ForeignKeys string representation vs ID depending on needs, 
            # here we just rely on string casting in _create_history.
            cls._create_history(task, changed_by, key, old_value, new_value)

        if "assigned_to" in kwargs:
            old_assignee = old_values.get("assigned_to")
            new_assignee = task.assigned_to
            if new_assignee and new_assignee != old_assignee:
                cls._notify_task_assigned(task)

        return task

    @classmethod
    @transaction.atomic
    def change_task_status(cls, task: Task, changed_by: User, new_status: str) -> Task:
        """Change task status, handle completion logic, award XP and record history."""
        old_status = task.status
        if old_status == new_status:
            return task

        task.status = new_status

        if new_status == TaskStatus.DONE and old_status != TaskStatus.DONE:
            task.completed_at = timezone.now()
        else:
            task.completed_at = None

        task.save(update_fields=['status', 'completed_at'])
        cls._create_history(task, changed_by, 'status', old_status, new_status)

        # === Геймификация ===
        if new_status == TaskStatus.DONE:
            # Начисляем XP тому, кому назначена задача
            assignee = task.assigned_to
            if assignee:
                engine = GamificationEngine(assignee)
                engine.award_xp('task_done', task=task)
            cls._notify_telegram_task_completed(task, changed_by)
            cls._notify_in_app_task_completed(task, changed_by)

        # Отправляем сигнал (если где-то используется)
        # Pass assignee as the user who should receive XP, not the one who changed the status
        task_completed.send(sender=cls, task=task, user=task.assigned_to or changed_by)

        return task

    @classmethod
    def add_comment(cls, task: Task, author: User, body: str) -> Comment:
        """Add a comment to a task."""
        comment = Comment.objects.create(
            task=task,
            author=author,
            body=body
        )
        # Award XP for commenting
        from apps.gamification.services import LevelUpService
        LevelUpService.award_xp(author, action='comment', task=task, note=f"Commented on task: {task.title}")
        return comment

    @classmethod
    @transaction.atomic
    def bulk_update_status(cls, tasks_qs: QuerySet[Task], changed_by: User, new_status: str) -> int:
        """Update status for multiple tasks at once."""
        count = 0
        for task in tasks_qs:
            if task.status != new_status:
                cls.change_task_status(task, changed_by, new_status)
                count += 1
        return count

    @staticmethod
    def _enqueue_after_commit(celery_task, *args) -> None:
        """Schedule a Celery task only after the DB transaction commits."""
        transaction.on_commit(lambda: celery_task.delay(*args))

    @staticmethod
    def _notify_task_assigned(task: Task) -> None:
        assignee = task.assigned_to
        if not assignee:
            return
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_task_assigned(assignee, task)
        except Exception as exc:
            logger.warning(
                "Failed to create in-app task-assigned notification for task %s: %s",
                task.pk,
                exc,
            )
        TaskService._notify_telegram_new_task(task)

    @staticmethod
    def _notify_telegram_new_task(task: Task) -> None:
        """
        TZ 6.6: Send Telegram notification when a task is assigned to an employee.
        Non-blocking — never breaks the main flow.
        """
        assignee = task.assigned_to
        if not assignee:
            return
        try:
            from apps.telegram_bot.tasks import send_new_task_notification
            TaskService._enqueue_after_commit(
                send_new_task_notification,
                assignee.id,
                task.id,
            )
        except Exception as exc:
            logger.warning(
                "Failed to queue Telegram new-task notification for task %s: %s",
                task.pk,
                exc,
            )

    @staticmethod
    def _notify_in_app_task_completed(task: Task, changed_by: User) -> None:
        """In-app team alerts for managers/admins when an employee completes a task."""
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_task_completed_team(task, changed_by)
        except Exception as exc:
            logger.warning(
                "Failed to create in-app task-completed notification for task %s: %s",
                task.pk,
                exc,
            )

    @staticmethod
    def _notify_telegram_task_completed(task: Task, changed_by: User) -> None:
        """
        TZ 6.6: Notify managers/admins when an employee completes a task.
        Non-blocking — never breaks the main flow.
        """
        try:
            from apps.telegram_bot.tasks import send_task_completed_notification
            TaskService._enqueue_after_commit(
                send_task_completed_notification,
                task.id,
                changed_by.id,
            )
        except Exception as exc:
            logger.warning(
                "Failed to queue Telegram task-completed notification for task %s: %s",
                task.pk,
                exc,
            )

