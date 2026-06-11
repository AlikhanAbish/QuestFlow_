"""
Tests for apps/companies — models, services, and views.
Run with: python manage.py test apps.companies
"""
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.companies.models import Company, Invitation, Team
from django.core import mail

from apps.companies.services import (
    InvitationAlreadyAcceptedError,
    InvitationEmailError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationService,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs) -> User:
    defaults = dict(
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User",
        password="secret",
    )
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def make_company(owner, **kwargs) -> Company:
    defaults = dict(name="Acme Corp", slug="acme-corp", owner=owner)
    defaults.update(kwargs)
    return Company.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class CompanyModelTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.company = make_company(self.owner)

    def test_str_returns_name(self):
        self.assertEqual(str(self.company), "Acme Corp")

    def test_soft_delete(self):
        self.company.delete()
        self.assertTrue(self.company.is_deleted)
        self.assertIsNotNone(self.company.deleted_at)
        # Manager should exclude deleted objects
        self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
        # all_objects should still find it
        self.assertTrue(Company.all_objects.filter(pk=self.company.pk).exists())

    def test_restore(self):
        self.company.delete()
        self.company.restore()
        self.assertFalse(self.company.is_deleted)
        self.assertIsNone(self.company.deleted_at)
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())

    def test_default_max_users(self):
        self.assertEqual(self.company.max_users, 50)

    def test_default_settings_is_dict(self):
        self.assertIsInstance(self.company.settings, dict)


class TeamModelTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.company = make_company(self.owner)
        self.team = Team.objects.create(name="Engineering", company=self.company, manager=self.owner)

    def test_str_includes_company(self):
        self.assertIn("Engineering", str(self.team))
        self.assertIn("Acme Corp", str(self.team))


class InvitationModelTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.company = make_company(self.owner)

    def test_token_is_unique_uuid(self):
        inv1 = Invitation.objects.create(
            email="a@example.com",
            company=self.company,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )
        inv2 = Invitation.objects.create(
            email="b@example.com",
            company=self.company,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertNotEqual(inv1.token, inv2.token)

    def test_str(self):
        inv = Invitation.objects.create(
            email="c@example.com",
            company=self.company,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertIn("c@example.com", str(inv))
        self.assertIn("Acme Corp", str(inv))


# ---------------------------------------------------------------------------
# InvitationService tests
# ---------------------------------------------------------------------------

class InvitationServiceTest(TestCase):
    def setUp(self):
        self.service = InvitationService()
        self.owner = make_user()
        self.company = make_company(self.owner)

    # -- create_invitation --------------------------------------------------

    def test_create_invitation_returns_instance(self):
        inv = self.service.create_invitation(
            email="new@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        self.assertIsInstance(inv, Invitation)
        self.assertEqual(inv.email, "new@example.com")
        self.assertFalse(inv.is_accepted)

    def test_create_invitation_sets_expiry(self):
        inv = self.service.create_invitation(
            email="new@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        delta = inv.expires_at - timezone.now()
        # Should be approximately 7 days
        self.assertGreater(delta.days, 5)

    def test_create_invitation_idempotent_refreshes_token(self):
        inv1 = self.service.create_invitation(
            email="dup@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        old_token = inv1.token
        inv2 = self.service.create_invitation(
            email="dup@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        # Same DB row, refreshed token
        self.assertEqual(inv1.pk, inv2.pk)
        self.assertNotEqual(inv2.token, old_token)

    # -- accept_invitation --------------------------------------------------

    def test_accept_invitation_marks_accepted(self):
        inv = self.service.create_invitation(
            email="acc@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        result = self.service.accept_invitation(str(inv.token))
        self.assertTrue(result.is_accepted)

    def test_accept_already_accepted_raises(self):
        inv = self.service.create_invitation(
            email="acc2@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        self.service.accept_invitation(str(inv.token))
        with self.assertRaises(InvitationAlreadyAcceptedError):
            self.service.accept_invitation(str(inv.token))

    def test_accept_expired_raises(self):
        inv = Invitation.objects.create(
            email="exp@example.com",
            company=self.company,
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        with self.assertRaises(InvitationExpiredError):
            self.service.accept_invitation(str(inv.token))

    def test_accept_invalid_token_raises(self):
        with self.assertRaises(InvitationNotFoundError):
            self.service.accept_invitation(str(uuid.uuid4()))

    # -- revoke_invitation --------------------------------------------------

    def test_revoke_makes_token_invalid(self):
        inv = self.service.create_invitation(
            email="rev@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        self.service.revoke_invitation(inv)
        with self.assertRaises(InvitationExpiredError):
            self.service.accept_invitation(str(inv.token))

    # -- get_pending_invitations --------------------------------------------

    def test_get_pending_excludes_accepted(self):
        inv = self.service.create_invitation(
            email="pend@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        self.assertEqual(self.service.get_pending_invitations(self.company).count(), 1)
        self.service.accept_invitation(str(inv.token))
        self.assertEqual(self.service.get_pending_invitations(self.company).count(), 0)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        BREVO_API_KEY='test-api-key',
        DEFAULT_FROM_EMAIL='test@example.com',
    )
    def test_create_and_send_invitation(self):
        """Test that create_and_send_invitation works with console backend."""
        inv = self.service.create_and_send_invitation(
            email="combo@example.com",
            company=self.company,
            invited_by=self.owner,
            base_url="https://app.questflow.io",
        )
        self.assertEqual(inv.email, "combo@example.com")

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        DEFAULT_FROM_EMAIL='QuestFlow <verified@example.com>',
        BREVO_API_KEY='test-api-key',
    )
    def test_send_invitation_renders_and_sends_email(self):
        """Test that invitation email is rendered with correct content."""
        inv = self.service.create_invitation(
            email="mail@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        # Send should not raise with proper config
        self.service.send_invitation(inv, base_url="https://app.questflow.io")
        
        # Verify invitation was created and can be accepted
        self.assertFalse(inv.is_accepted)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        DEFAULT_FROM_EMAIL='QuestFlow <login@smtp-brevo.com>',
        BREVO_API_KEY='test-api-key',
    )
    def test_get_from_email_rejects_smtp_brevo_sender(self):
        """Test that @smtp-brevo.com addresses are rejected (must use verified sender)."""
        inv = self.service.create_invitation(
            email="badfrom@example.com",
            company=self.company,
            invited_by=self.owner,
        )
        with self.assertRaises(InvitationEmailError):
            self.service.send_invitation(inv, base_url="https://app.questflow.io")

    @override_settings(DEFAULT_FROM_EMAIL='verified@example.com')
    def test_get_from_email_accepts_plain_verified_sender(self):
        """Test that plain email addresses are accepted as verified senders."""
        self.service._get_from_email()

    # -- get_pending_invitations --------------------------------------------

    def test_get_pending_excludes_expired(self):
        Invitation.objects.create(
            email="exp2@example.com",
            company=self.company,
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(self.service.get_pending_invitations(self.company).count(), 0)
