"""
TelegramService — business logic layer for Telegram operations.

Responsibilities:
  - generate_connect_token: resets/returns the connect_token for /profile/ UI
  - link_account: creates or updates TelegramUser when /start <token> is received
  - send_message: thin synchronous wrapper around Bot.send_message (used by Celery)
  - send_message_async: async version for use inside python-telegram-bot handlers
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    User = get_user_model()

logger = logging.getLogger(__name__)


class TelegramService:
    # ------------------------------------------------------------------
    # Account linking
    # ------------------------------------------------------------------

    @staticmethod
    def generate_connect_token(user: "User") -> str:
        """
        Return (and optionally rotate) a connect_token for the given user.
        If the user already has a TelegramUser, rotate the token so each
        /profile/ visit shows a fresh one-time link.
        """
        from .models import TelegramUser

        tg_user, created = TelegramUser.objects.get_or_create(
            user=user,
            defaults={
                "telegram_id": None,
                "is_active": False,
            },
        )
        if not created:
            # Rotate the token so each page-load is a fresh link
            tg_user.connect_token = uuid.uuid4()
            tg_user.save(update_fields=["connect_token"])
        return str(tg_user.connect_token)

    @staticmethod
    def link_account(
        token: str,
        telegram_id: int,
        username: str = "",
        first_name: str = "",
    ) -> "TelegramUser | None":
        """
        Called from /start <token> handler.
        Finds the TelegramUser with matching connect_token or user_id, sets telegram_id,
        marks it active. Returns None if token is invalid.
        """
        from .models import TelegramUser
        import uuid

        token_clean = token
        if token.startswith("connect_"):
            token_clean = token[8:]

        tg_user = None
        # Try to find by UUID connect_token first
        try:
            uuid.UUID(token_clean)
            tg_user = TelegramUser.objects.select_related("user").get(
                connect_token=token_clean
            )
        except (ValueError, TelegramUser.DoesNotExist):
            # Fallback to query by user_id
            try:
                user_id = int(token_clean)
                tg_user, created = TelegramUser.objects.select_related("user").get_or_create(
                    user_id=user_id,
                    defaults={
                        "telegram_id": telegram_id,
                        "is_active": True,
                    }
                )
                if not created:
                    tg_user.telegram_id = telegram_id
                    tg_user.is_active = True
            except (ValueError, TelegramUser.DoesNotExist, Exception) as exc:
                logger.warning("link_account: invalid token or user_id %s: %s", token, exc)
                return None

        if tg_user:
            # If another Telegram account already used this telegram_id, update it
            TelegramUser.objects.filter(telegram_id=telegram_id).exclude(
                pk=tg_user.pk
            ).delete()

            tg_user.telegram_id = telegram_id
            tg_user.username = username or ""
            tg_user.first_name = first_name or ""
            tg_user.is_active = True
            tg_user.connect_token = uuid.uuid4()  # Invalidate used token
            tg_user.save(update_fields=["telegram_id", "username", "first_name", "is_active", "connect_token"])

            logger.info(
                "link_account: linked user %s → telegram_id=%s",
                tg_user.user.email,
                telegram_id,
            )
            return tg_user
        return None

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------

    @staticmethod
    def send_message(
        telegram_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> bool:
        """
        Synchronous fire-and-forget send, safe to call from Celery tasks.
        Returns True on success, False on failure.
        """
        import httpx

        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == "your-telegram-bot-token":
            logger.debug("send_message: TELEGRAM_BOT_TOKEN not configured, skipping.")
            return False

        payload: dict = {
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            resp = httpx.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            detail = ""
            if hasattr(exc, "response") and exc.response is not None:
                detail = f" — {exc.response.text[:300]}"
            logger.error("send_message to %s failed: %s%s", telegram_id, exc, detail)
            return False

    @staticmethod
    async def send_message_async(
        telegram_id: int, text: str, parse_mode: str = "HTML"
    ) -> bool:
        """
        Async version for use inside python-telegram-bot handler coroutines.
        """
        from .bot import get_bot

        bot = get_bot()
        if bot is None:
            return False
        try:
            await bot.send_message(
                chat_id=telegram_id, text=text, parse_mode=parse_mode
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("send_message_async to %s failed: %s", telegram_id, exc)
            return False
