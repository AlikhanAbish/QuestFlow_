from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Role
from apps.companies.models import Company
from apps.gamification.models import UserLevel
from apps.gamification.services import LeaderboardService

User = get_user_model()


class LeaderboardServiceTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Acme",
            slug="acme",
            owner_id=1,
        )
        self.admin = User.objects.create_user(
            email="admin@acme.com",
            username="admin",
            first_name="Admin",
            last_name="User",
            password="secret",
            role=Role.ADMIN,
            company=self.company,
        )
        self.company.owner = self.admin
        self.company.save(update_fields=["owner"])

        self.employee = User.objects.create_user(
            email="emp@acme.com",
            username="emp",
            first_name="Emp",
            last_name="One",
            password="secret",
            role=Role.EMPLOYEE,
            company=self.company,
        )
        emp_level, _ = UserLevel.objects.get_or_create(user=self.employee)
        emp_level.level = 3
        emp_level.total_xp = 500
        emp_level.save(update_fields=["level", "total_xp"])

        admin_level, _ = UserLevel.objects.get_or_create(user=self.admin)
        admin_level.level = 10
        admin_level.total_xp = 9999
        admin_level.save(update_fields=["level", "total_xp"])

    def test_excludes_admin_and_manager(self):
        board = LeaderboardService.get_company_leaderboard(company=self.company)
        emails = {entry["name"] for entry in board}
        self.assertEqual(len(board), 1)
        self.assertIn("Emp One", emails)
        self.assertNotIn("Admin User", emails)
