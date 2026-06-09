"""
Shared helpers for Telegram notification Celery tasks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.urls import reverse

from apps.accounts.models import Role

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    User = get_user_model()

BURNOUT_EMOJIS = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
BURNOUT_LABELS = {"green": "Healthy", "yellow": "At Risk", "red": "Burned Out"}
PRIORITY_EMOJIS = {1: "🟢", 2: "🟡", 3: "🔴", 4: "⚫"}
MILESTONE_LEVELS = {10, 20, 30, 40, 50}


def web_url(view_name: str, *args) -> str:
    """Build an absolute URL for inline keyboard buttons."""
    path = reverse(view_name, args=args)
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def supports_inline_buttons() -> bool:
    """
    Telegram rejects inline keyboard URLs like http://localhost:8000/...
    Buttons work only with a public HTTPS SITE_URL (e.g. ngrok / production).
    """
    return settings.SITE_URL.rstrip("/").startswith("https://")


def build_inline_keyboard(button_rows: list[list[dict]]) -> dict:
    """Convert button dicts to Telegram inline_keyboard reply_markup."""
    return {"inline_keyboard": button_rows}


def prepare_message(
    text: str,
    button_rows: list[list[dict]] | None = None,
) -> tuple[str, dict | None]:
    """
    Return (text, reply_markup).
    On localhost/dev, fall back to HTML links in the message body.
    """
    if not button_rows:
        return text, None

    if supports_inline_buttons():
        return text, build_inline_keyboard(button_rows)

    links = [
        f"👉 <a href='{btn['url']}'>{btn['text']}</a>"
        for row in button_rows
        for btn in row
        if btn.get("url") and btn.get("text")
    ]
    if links:
        text = text.rstrip() + "\n\n" + "\n".join(links)
    return text, None


def format_burnout_level(level: str) -> str:
    emoji = BURNOUT_EMOJIS.get(level, "❓")
    label = BURNOUT_LABELS.get(level, level)
    return f"{emoji} {label}"


def format_deadline(deadline) -> str:
    if not deadline:
        return "No deadline"
    return deadline.strftime("%b %d, %Y at %H:%M")


def get_team_notification_recipients(team) -> list:
    """
    Managers and admins who should receive team-level alerts.

    Managers are resolved from (in order):
      1. Team.manager FK
      2. Users who manage this team (managed_teams)
      3. Manager-role users assigned to this team (user.team) — common when
         Team.manager was never set in admin/UI
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    recipients: list = []
    seen: set[int] = set()

    def add(user) -> None:
        if user and user.is_active and user.pk not in seen:
            recipients.append(user)
            seen.add(user.pk)

    if team.manager_id:
        add(team.manager)

    for mgr in User.objects.filter(
        managed_teams=team,
        role=Role.MANAGER,
        is_active=True,
    ):
        add(mgr)

    for mgr in User.objects.filter(
        team=team,
        role=Role.MANAGER,
        is_active=True,
    ):
        add(mgr)

    for admin in User.objects.filter(
        company_id=team.company_id,
        role=Role.ADMIN,
        is_active=True,
    ):
        add(admin)

    return recipients


def get_employee_alert_recipients(employee) -> list:
    """Managers and admins who should receive alerts about an employee."""
    team = getattr(employee, "team", None)
    if team:
        return get_team_notification_recipients(team)

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not employee.company_id:
        return []

    return list(
        User.objects.filter(
            company_id=employee.company_id,
            role=Role.ADMIN,
            is_active=True,
        )
    )


def send_to_recipients(
    recipients: list,
    text: str,
    *,
    button_rows: list[list[dict]] | None = None,
) -> int:
    """Send a message to all linked Telegram accounts among recipients."""
    from .models import TelegramUser
    from .services import TelegramService

    if not recipients:
        return 0

    recipient_ids = [user.pk for user in recipients]
    text, markup = prepare_message(text, button_rows)

    sent = 0
    tg_users = TelegramUser.objects.filter(
        user_id__in=recipient_ids,
        is_active=True,
        telegram_id__gt=0,
    )
    for tg_user in tg_users:
        if TelegramService.send_message(
            tg_user.telegram_id,
            text,
            reply_markup=markup,
        ):
            sent += 1
    return sent


def send_to_user(
    user,
    text: str,
    *,
    button_rows: list[list[dict]] | None = None,
) -> bool:
    """Send a message to a single user's linked Telegram account."""
    return send_to_recipients([user], text, button_rows=button_rows) > 0
