import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.telegram_bot.models import TelegramUser
from apps.telegram_bot.services import TelegramService
from apps.companies.models import Company, Team
from apps.telegram_bot.handlers import (
    start_handler,
    get_profile_data,
    get_tasks_data,
    format_start_profile_summary,
    format_profile_message,
    format_tasks_message,
    build_tasks_keyboard,
    is_manager_or_admin,
)

User = get_user_model()


class TelegramBotTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test_tg_user@example.com",
            username="test_tg_user",
            first_name="Telegram",
            last_name="Tester",
            password="testpassword123",
            role="employee",
        )
        self.client = Client()

    def test_generate_connect_token(self):
        token = TelegramService.generate_connect_token(self.user)
        self.assertTrue(uuid.UUID(token))

        tg_user = TelegramUser.objects.get(user=self.user)
        self.assertFalse(tg_user.is_active)
        self.assertIsNone(tg_user.telegram_id)
        self.assertEqual(str(tg_user.connect_token), token)

    def test_multiple_users_generate_connect_token(self):
        user2 = User.objects.create_user(
            email="test_tg_user2@example.com",
            username="test_tg_user2",
            first_name="Second",
            last_name="User",
            password="testpassword123",
            role="manager",
        )
        TelegramService.generate_connect_token(self.user)
        TelegramService.generate_connect_token(user2)

        self.assertEqual(TelegramUser.objects.count(), 2)
        self.assertIsNone(TelegramUser.objects.get(user=self.user).telegram_id)
        self.assertIsNone(TelegramUser.objects.get(user=user2).telegram_id)

    def test_link_account_with_uuid(self):
        token = TelegramService.generate_connect_token(self.user)

        linked = TelegramService.link_account(
            token=token,
            telegram_id=123456789,
            username="tg_tester",
            first_name="TG",
        )

        self.assertIsNotNone(linked)
        self.assertEqual(linked.user, self.user)
        self.assertEqual(linked.telegram_id, 123456789)
        self.assertEqual(linked.username, "tg_tester")
        self.assertEqual(linked.first_name, "TG")
        self.assertTrue(linked.is_active)

        self.assertNotEqual(str(linked.connect_token), token)

    def test_link_account_with_user_id_prefix(self):
        TelegramService.generate_connect_token(self.user)

        linked = TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=987654321,
            username="tg_tester2",
            first_name="TG2",
        )

        self.assertIsNotNone(linked)
        self.assertEqual(linked.user, self.user)
        self.assertEqual(linked.telegram_id, 987654321)
        self.assertTrue(linked.is_active)

    def test_connect_view_requires_login(self):
        response = self.client.get(reverse("telegram_bot:connect"))
        self.assertEqual(response.status_code, 302)

    def test_connect_view_returns_widget(self):
        self.client.login(email="test_tg_user@example.com", password="testpassword123")

        response = self.client.get(reverse("telegram_bot:connect"))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("telegram-connect-widget", content)
        self.assertIn("connect_", content)
        self.assertIn("Connect Telegram", content)
        self.assertIn("Start Bot", content)

    def test_connect_view_manager(self):
        manager = User.objects.create_user(
            email="manager@example.com",
            username="mgr_user",
            first_name="Mgr",
            last_name="User",
            password="testpassword123",
            role="manager",
        )
        self.client.login(email="manager@example.com", password="testpassword123")
        response = self.client.get(reverse("telegram_bot:connect"))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Connect Telegram", content)
        self.assertIn(f"connect_{manager.id}", content)

    def test_connect_view_admin(self):
        admin = User.objects.create_user(
            email="admin@example.com",
            username="admin_user",
            first_name="Admin",
            last_name="User",
            password="testpassword123",
            role="admin",
        )
        self.client.login(email="admin@example.com", password="testpassword123")
        response = self.client.get(reverse("telegram_bot:connect"))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Connect Telegram", content)
        self.assertIn(f"connect_{admin.id}", content)

    def test_connect_view_linked_shows_open_buttons(self):
        TelegramService.generate_connect_token(self.user)
        TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=555555,
            username="linked",
            first_name="Linked",
        )
        self.client.login(email="test_tg_user@example.com", password="testpassword123")
        response = self.client.get(reverse("telegram_bot:connect"))
        content = response.content.decode()
        self.assertIn("Telegram Connected", content)
        self.assertIn("Open in Telegram", content)
        self.assertIn("Start Bot", content)

    def test_get_profile_data_linked_user(self):
        TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=777777,
            username="stats_user",
            first_name="Stats",
        )
        profile = get_profile_data(777777)
        self.assertIsNotNone(profile)
        self.assertIn("level", profile)
        self.assertIn("streak", profile)
        self.assertIn("burnout_text", profile)
        self.assertEqual(profile["role"], "employee")
        self.assertEqual(profile["role_label"], "Employee")
        self.assertNotIn("leaderboard", profile)

    def test_get_profile_data_manager_includes_team_sections(self):
        company = Company.objects.create(name="TG Co", slug="tg-co", owner_id=1)
        self.user.company = company
        self.user.role = "manager"
        self.user.save(update_fields=["company", "role"])
        team = Team.objects.create(name="Alpha", company=company, manager=self.user)
        self.user.team = team
        self.user.save(update_fields=["team"])

        TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=666666,
            username="mgr",
            first_name="Mgr",
        )
        profile = get_profile_data(666666)
        self.assertEqual(profile["role"], "manager")
        self.assertIn("leaderboard", profile)
        self.assertIn("burnout_stats", profile)
        self.assertIn("team_summary", profile)
        text = format_profile_message(profile)
        self.assertIn("Team Leaderboard", text)
        self.assertIn("Team Burnout", text)
        self.assertIn("Team Stats", text)
        self.assertNotIn("Total XP", text)
        self.assertNotIn("Weekly XP", text)
        self.assertNotIn("Streak", text)

    def test_link_account_preserves_user_role(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        TelegramService.generate_connect_token(self.user)
        linked = TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=333333,
            username="admin_tg",
            first_name="Admin",
        )
        self.assertEqual(linked.user.role, "admin")

    def test_employee_tasks_keyboard_has_no_create_button(self):
        keyboard = build_tasks_keyboard("employee")
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        self.assertNotIn("➕ Create Task", button_texts)

    def test_manager_tasks_keyboard_has_create_button(self):
        keyboard = build_tasks_keyboard("manager")
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        self.assertIn("➕ Create Task", button_texts)

    def test_get_tasks_data_employee_sees_only_own_tasks(self):
        from apps.tasks.models import Task, TaskStatus

        company = Company.objects.create(name="Task Co", slug="task-co", owner_id=1)
        self.user.company = company
        self.user.save(update_fields=["company"])

        other = User.objects.create_user(
            email="other@example.com",
            username="other_user",
            first_name="Other",
            last_name="User",
            password="testpassword123",
            role="employee",
            company=company,
        )

        Task.objects.create(
            title="My task",
            company=company,
            assigned_to=self.user,
            created_by=self.user,
            status=TaskStatus.TODO,
        )
        Task.objects.create(
            title="Someone else's task",
            company=company,
            assigned_to=other,
            created_by=other,
            status=TaskStatus.TODO,
        )

        TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=111111,
            username="emp",
            first_name="Emp",
        )
        data = get_tasks_data(111111)
        self.assertEqual(data["role"], "employee")
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["title"], "My task")

    def test_format_tasks_message_employee_no_create_hint(self):
        text = format_tasks_message({"role": "employee", "tasks": []})
        self.assertIn("Your Tasks", text)
        self.assertNotIn("Team Active", text)

    def test_format_start_profile_summary(self):
        text = format_start_profile_summary({
            "name": "Test User",
            "role": "employee",
            "role_label": "Employee",
            "level": 3,
            "streak": 5,
            "burnout_text": "🟢 Healthy",
        })
        self.assertIn("Level", text)
        self.assertIn("Streak", text)
        self.assertIn("Burnout", text)
        self.assertIn("Employee", text)

    def test_format_start_profile_summary_manager_no_personal_stats(self):
        text = format_start_profile_summary({
            "name": "Mgr User",
            "role": "manager",
            "role_label": "Manager",
            "level": 1,
            "streak": 1,
            "burnout_text": "❓ Not assessed",
            "leaderboard": [{"rank": 1, "name": "Emp", "level": 2, "xp": 100, "is_me": False}],
            "burnout_stats": {"green": 0, "yellow": 0, "red": 1, "total": 1},
            "team_name": "sales",
            "team_summary": {
                "total_members": 2,
                "active_tasks": 1,
                "done_tasks": 1,
                "overdue_tasks": 0,
                "total_xp": 684,
            },
        })
        self.assertIn("Team Leaderboard", text)
        self.assertNotIn("Streak", text)
        self.assertNotIn("Level:", text)

    def test_is_manager_or_admin(self):
        self.assertFalse(is_manager_or_admin("employee"))
        self.assertTrue(is_manager_or_admin("manager"))
        self.assertTrue(is_manager_or_admin("admin"))

    def _run_start_handler(self, args, telegram_id=888888):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = telegram_id
        update.effective_user.username = "tg_user"
        update.effective_user.first_name = "TG"
        update.message.reply_html = AsyncMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = args

        asyncio.run(start_handler(update, context))
        return update

    def test_start_without_args_linked(self):
        TelegramService.link_account(
            token=f"connect_{self.user.id}",
            telegram_id=888888,
            username="start_user",
            first_name="Start",
        )
        update = self._run_start_handler([])
        update.message.reply_html.assert_called_once()
        text = update.message.reply_html.call_args[0][0]
        self.assertIn("Welcome back", text)
        self.assertIn("Level", text)
        self.assertIn("Streak", text)
        self.assertIn("Burnout", text)

    def test_start_without_args_unlinked(self):
        update = self._run_start_handler([], telegram_id=999999)
        update.message.reply_html.assert_called_once()
        text = update.message.reply_html.call_args[0][0]
        self.assertIn("Connect Telegram", text)

    def test_start_with_connect_user_id(self):
        TelegramService.generate_connect_token(self.user)
        update = self._run_start_handler([f"connect_{self.user.id}"], telegram_id=444444)
        update.message.reply_html.assert_called_once()
        text = update.message.reply_html.call_args[0][0]
        self.assertIn("Account linked", text)
        self.assertTrue(
            TelegramUser.objects.filter(user=self.user, telegram_id=444444, is_active=True).exists()
        )

    @patch("apps.telegram_bot.views.process_webhook_update", new_callable=AsyncMock)
    @patch("apps.telegram_bot.views.get_application")
    def test_webhook_view(self, mock_get_app, mock_process):
        mock_bot = MagicMock()
        mock_app = MagicMock()
        mock_app.bot = mock_bot
        mock_get_app.return_value = mock_app

        payload = {
            "update_id": 10000,
            "message": {
                "message_id": 1,
                "date": 1441645517,
                "chat": {
                    "id": 111111,
                    "type": "private",
                    "username": "test_user",
                },
                "from": {
                    "id": 111111,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "test_user",
                },
                "text": "/start",
            },
        }

        response = self.client.post(
            reverse("telegram_bot:webhook"),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_process.called)


class TelegramNotificationTaskTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Notify Co", slug="notify-co", owner_id=1)
        self.manager = User.objects.create_user(
            email="mgr@notify.com",
            username="mgr_notify",
            first_name="Manager",
            last_name="User",
            password="testpassword123",
            role="manager",
            company=self.company,
        )
        self.employee = User.objects.create_user(
            email="emp@notify.com",
            username="emp_notify",
            first_name="Employee",
            last_name="User",
            password="testpassword123",
            role="employee",
            company=self.company,
        )
        self.team = Team.objects.create(
            name="Sales",
            company=self.company,
            manager=self.manager,
        )
        self.employee.team = self.team
        self.employee.save(update_fields=["team"])
        self.manager.team = self.team
        self.manager.save(update_fields=["team"])

        TelegramService.link_account(
            token=f"connect_{self.employee.id}",
            telegram_id=100001,
            username="emp_tg",
            first_name="Emp",
        )
        TelegramService.link_account(
            token=f"connect_{self.manager.id}",
            telegram_id=100002,
            username="mgr_tg",
            first_name="Mgr",
        )

    @patch("apps.telegram_bot.notifications.TelegramService.send_message", return_value=True)
    def test_send_new_task_notification_employee_only(self, mock_send):
        from apps.tasks.models import Task, TaskStatus
        from apps.telegram_bot.tasks import send_new_task_notification

        task = Task.objects.create(
            title="New feature",
            company=self.company,
            team=self.team,
            assigned_to=self.employee,
            created_by=self.manager,
            status=TaskStatus.TODO,
        )
        result = send_new_task_notification(self.employee.id, task.id)
        self.assertTrue(result["sent"])
        mock_send.assert_called_once()
        text = mock_send.call_args[0][1]
        self.assertIn("New Task Assigned", text)
        self.assertIn("New feature", text)
        self.assertIn("reply_markup", mock_send.call_args[1])

    @patch("apps.telegram_bot.notifications.TelegramService.send_message", return_value=True)
    def test_send_new_task_notification_skips_manager(self, mock_send):
        from apps.tasks.models import Task, TaskStatus
        from apps.telegram_bot.tasks import send_new_task_notification

        task = Task.objects.create(
            title="Manager task",
            company=self.company,
            assigned_to=self.manager,
            created_by=self.manager,
            status=TaskStatus.TODO,
        )
        result = send_new_task_notification(self.manager.id, task.id)
        self.assertFalse(result["sent"])
        mock_send.assert_not_called()

    @patch("apps.telegram_bot.notifications.TelegramService.send_message", return_value=True)
    def test_send_milestone_notification_to_manager(self, mock_send):
        from apps.telegram_bot.tasks import send_milestone_notification

        result = send_milestone_notification(self.employee.id, 10)
        self.assertEqual(result["sent"], 1)
        text = mock_send.call_args[0][1]
        self.assertIn("Milestone Achievement", text)
        self.assertIn("Employee User", text)
        self.assertIn("Level 10", text)

    @patch("apps.telegram_bot.notifications.TelegramService.send_message", return_value=True)
    def test_get_team_recipients_when_team_manager_fk_unset(self):
        from apps.telegram_bot.notifications import get_team_notification_recipients

        self.team.manager = None
        self.team.save(update_fields=["manager"])

        recipients = get_team_notification_recipients(self.team)
        emails = {r.email for r in recipients}
        self.assertIn(self.manager.email, emails)

    def test_send_task_completed_notification(self, mock_send):
        from apps.tasks.models import Task, TaskStatus
        from apps.telegram_bot.tasks import send_task_completed_notification

        task = Task.objects.create(
            title="Done task",
            company=self.company,
            team=self.team,
            assigned_to=self.employee,
            created_by=self.manager,
            status=TaskStatus.DONE,
        )
        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])

        result = send_task_completed_notification(task.id, self.employee.id)
        self.assertEqual(result["sent"], 1)
        text = mock_send.call_args[0][1]
        self.assertIn("Task Completed", text)
        self.assertIn("Done task", text)

    @patch("apps.telegram_bot.notifications.TelegramService.send_message", return_value=True)
    def test_send_level_up_notification_skips_manager(self, mock_send):
        from apps.telegram_bot.tasks import send_level_up_notification

        result = send_level_up_notification(self.manager.id, 2)
        self.assertFalse(result["sent"])
        self.assertEqual(result["reason"], "not_employee")
        mock_send.assert_not_called()

    def test_send_team_burnout_notification(self, mock_send):
        from apps.burnout.models import BurnoutScore
        from apps.telegram_bot.tasks import send_team_burnout_notification

        BurnoutScore.objects.create(
            user=self.employee,
            score="red",
            manager_consent=True,
            exhaustion_avg=4.0,
            cynicism_avg=4.0,
            efficacy_avg=2.0,
        )

        result = send_team_burnout_notification(
            self.team.id, self.employee.id, "yellow", "red"
        )
        self.assertEqual(result["sent"], 1)
        text = mock_send.call_args[0][1]
        self.assertIn("Team Burnout Updated", text)
        self.assertIn("Sales", text)
