from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.core.models import SoftDeleteModel, TimeStampedModel
from apps.companies.models import Company, Team


class Priority(models.IntegerChoices):
    LOW = 1, _('Low')
    MEDIUM = 2, _('Medium')
    HIGH = 3, _('High')
    CRITICAL = 4, _('Critical')


class TaskStatus(models.TextChoices):
    TODO = 'todo', _('To Do')
    IN_PROGRESS = 'in_progress', _('In Progress')
    DONE = 'done', _('Done')
    OVERDUE = 'overdue', _('Overdue')


class Task(SoftDeleteModel):
    title = models.CharField(max_length=500, verbose_name=_('title'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_('company'))
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('team'))
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        verbose_name=_('created by')
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks',
        verbose_name=_('assigned to')
    )
    
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices, 
        default=TaskStatus.TODO,
        verbose_name=_('status')
    )
    priority = models.IntegerField(
        choices=Priority.choices, 
        default=Priority.MEDIUM,
        verbose_name=_('priority')
    )
    
    deadline = models.DateTimeField(null=True, blank=True, verbose_name=_('deadline'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('completed at'))

    class Meta:
        verbose_name = _('task')
        verbose_name_plural = _('tasks')
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Comment(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name=_('task'))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('author'))
    body = models.TextField(max_length=2000, verbose_name=_('body'))

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.task}'


class TaskHistory(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history', verbose_name=_('task'))
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('changed by'))
    field_name = models.CharField(max_length=100, verbose_name=_('field name'))
    old_value = models.TextField(blank=True, verbose_name=_('old value'))
    new_value = models.TextField(blank=True, verbose_name=_('new value'))

    class Meta:
        verbose_name = _('task history')
        verbose_name_plural = _('task histories')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.field_name} changed for {self.task}'
