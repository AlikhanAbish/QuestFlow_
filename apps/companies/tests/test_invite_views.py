"""
Integration tests for invitation acceptance and registration flow.
Run with: python manage.py test apps.companies.tests.test_invite_views
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.companies.models import Company, Invitation
from apps.companies.services import InvitationService

User = get_user_model()


def make_user(**kwargs) -> User:
    defaults = dict(
        email="owner@example.com",
        username="owner",
        first_name="Owner",
        last_name="User",
        password="secret",
    )
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def make_company(owner, **kwargs) -> Company:
    defaults = dict(name="Acme Corp", slug="acme-corp", owner=owner)
    defaults.update(kwargs)
    return Company.objects.create(**defaults)


class InviteRegistrationFlowTest(TestCase):
    def setUp(self):
        self.service = InvitationService()
        self.owner = make_user()
        self.company = make_company(self.owner)
        self.invitation = self.service.create_invitation(
            email="newhire@example.com",
            company=self.company,
            invited_by=self.owner,
        )

    def test_accept_invite_redirects_to_register_with_token(self):
        response = self.client.get(
            reverse("companies:accept_invite", kwargs={"token": self.invitation.token})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/register/", response.url)
        self.assertIn(f"token={self.invitation.token}", response.url)

    def test_accept_invite_does_not_mark_accepted(self):
        self.client.get(
            reverse("companies:accept_invite", kwargs={"token": self.invitation.token})
        )
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.is_accepted)

    def test_register_get_shows_form_for_valid_token(self):
        response = self.client.get(
            reverse("accounts:register"),
            {"token": str(self.invitation.token)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Join the Team")
        self.assertContains(response, self.company.name)

    def test_register_get_without_token_redirects_to_login(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_authenticated_user_logged_out_on_invite_link(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("companies:accept_invite", kwargs={"token": self.invitation.token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Join the Team")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_register_post_marks_invitation_accepted(self):
        register_url = reverse("accounts:register")
        response = self.client.post(
            register_url,
            {
                "token": str(self.invitation.token),
                "username": "newhire",
                "first_name": "New",
                "last_name": "Hire",
                "email": self.invitation.email,
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertTrue(self.invitation.is_accepted)
        user = User.objects.get(email=self.invitation.email)
        self.assertEqual(user.company, self.company)

    def test_expired_invite_redirects_to_login(self):
        self.invitation.expires_at = timezone.now() - timedelta(hours=1)
        self.invitation.save(update_fields=["expires_at"])
        response = self.client.get(
            reverse("companies:accept_invite", kwargs={"token": self.invitation.token})
        )
        self.assertRedirects(response, reverse("accounts:login"))
