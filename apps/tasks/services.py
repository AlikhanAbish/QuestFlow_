from django.utils import timezone
from django.db import transaction
from typing import Any, Dict, List, Optional
from django.db.models import QuerySet

from .models import Task, Comment, TaskHistory, TaskStatus
from .signals import task_completed
from apps.companies.models import Company
from apps.accounts.models import User
from apps.gamification.engine import GamificationEngine

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

        # Отправляем сигнал (если где-то используется)
        task_completed.send(sender=cls, task=task, user=changed_by)

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
