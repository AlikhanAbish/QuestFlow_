from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from apps.gamification.models import UserLevel, Streak

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_gamification_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserLevel and Streak for newly created users.
    """
    if created:
        UserLevel.objects.get_or_create(user=instance)
        Streak.objects.get_or_create(user=instance)


from apps.tasks.signals import task_completed
from apps.gamification.engine import GamificationEngine

@receiver(task_completed)
def handle_task_completed(sender, task, user, **kwargs):
    """Award XP when a task is marked as Done."""
    engine = GamificationEngine(user)
    
    # Base XP for task completion
    action = 'task_done'
    
    # Check for early completion bonus
    if task.deadline and task.completed_at and task.completed_at <= task.deadline:
        action = 'task_done_early'
        
    engine.award_xp(action=action, task=task, note=f"Completed task: {task.title}")



