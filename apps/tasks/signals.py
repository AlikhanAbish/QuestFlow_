"""
Custom Django signals for the tasks application.

Usage (receiver example in gamification/signals.py):

    from apps.tasks.signals import task_completed

    @receiver(task_completed)
    def award_xp_on_task_done(sender, task, user, **kwargs):
        GamificationEngine.award_xp(user, action='task_completed', task=task)
"""

from django.dispatch import Signal

# Sent when a task transitions to status=DONE.
# Provides: task (Task instance), user (User who triggered the change).
task_completed = Signal()
