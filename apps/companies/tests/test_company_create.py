"""
Tests for company creation from Company Settings (admin/manager without company).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.companies.models import Company, Team
from apps.companies.services import company_service

User = get_user_model()


class CompanyCreateViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            first_name="Admin",
            last_name="User",
            password="secret",
            role=Role.ADMIN,
        )

    def test_settings_page_without_company_returns_200(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("companies:company_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your company")
        self.assertContains(response, "Create company")

    def test_create_company_assigns_user_and_redirects(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("companies:company_create"),
            {"name": "New Corp", "max_users": 25},
        )
        self.assertRedirects(response, reverse("companies:company_settings"))
        self.admin.refresh_from_db()
        self.assertIsNotNone(self.admin.company_id)
        company = Company.objects.get(pk=self.admin.company_id)
        self.assertEqual(company.name, "New Corp")
        self.assertEqual(company.owner, self.admin)
        self.assertEqual(company.slug, "new-corp")

    def test_create_company_with_teams(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("companies:company_create"),
            {
                "name": "Team Corp",
                "max_users": 50,
                "team_names": "Engineering, Sales\nSupport",
            },
        )
        self.assertRedirects(response, reverse("companies:company_settings"))
        company = Company.objects.get(name="Team Corp")
        team_names = set(Team.objects.filter(company=company).values_list("name", flat=True))
        self.assertEqual(team_names, {"Engineering", "Sales", "Support"})

    def test_parse_team_names(self):
        names = company_service.parse_team_names("A, B\nC\nA")
        self.assertEqual(names, ["A", "B", "C"])

    def test_settings_with_company_shows_invite_section(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("companies:company_create"),
            {"name": "Acme", "max_users": 50},
        )
        response = self.client.get(reverse("companies:company_settings"))
        self.assertContains(response, "Invite team members")
        self.assertContains(response, "Teams")
        self.assertNotContains(response, "Create your company")

    def test_add_team_on_settings_page(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("companies:company_create"),
            {"name": "Acme", "max_users": 50},
        )
        response = self.client.post(
            reverse("companies:team_create"),
            {"name": "Product"},
        )
        self.assertRedirects(response, reverse("companies:company_settings"))
        self.admin.refresh_from_db()
        self.assertTrue(
            Team.objects.filter(company_id=self.admin.company_id, name="Product").exists()
        )
