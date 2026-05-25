"""
TZ 5.7: TelegramUser model — links a Django User to a Telegram account.
Lives in apps/telegram_bot as specified in TZ 3.2.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class TelegramUser(TimeStampedModel):
    """
    Represents a Telegram account bound to a QuestFlow user.

    Fields:
        user          — one-to-one link to accounts.User
        telegram_id   — unique Telegram numeric user ID
        username      — Telegram @handle (optional)
        first_name    — Telegram display first name
        is_active     — whether the bot should send messages to this user
        connect_token — UUID token shown in /profile/ to link accounts via /start
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram",
    )
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Unset to stop all Telegram messages for this user.",
    )
    # One-time token: user clicks /start <token> in Telegram to confirm linking
    connect_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Token shown on /profile/telegram/connect/ — sent as /start payload.",
    )

    class Meta:
        verbose_name = "Telegram User"
        verbose_name_plural = "Telegram Users"

    def __str__(self) -> str:
        handle = f"@{self.username}" if self.username else str(self.telegram_id)
        return f"{self.user.email} → {handle}"
