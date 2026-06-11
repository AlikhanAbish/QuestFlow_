from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from apps.gamification.models import UserLevel, Streak, RealReward

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_gamification_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserLevel and Streak for newly created users.
    """
    if created:
        UserLevel.objects.get_or_create(user=instance)
        Streak.objects.get_or_create(user=instance)


# TZ 6.6: Telegram notification for RealReward
@receiver(post_save, sender=RealReward)
def notify_reward_created(sender, instance, created, **kwargs):
    """
    Send Telegram notification when a reward is granted to a user.
    """
    if created:
        try:
            from apps.telegram_bot.tasks import send_real_reward_notification
            send_real_reward_notification.delay(instance.recipient.id, instance.id)
        except Exception:
            # Telegram notification is non-critical
            pass

