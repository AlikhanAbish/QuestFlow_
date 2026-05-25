"""
Business logic for invitations.

All invitation-related operations go through InvitationService,
keeping views thin and logic testable in isolation.
"""
import logging
import smtplib
from datetime import timedelta
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Company, Invitation, Team
from apps.accounts.models import Role

logger = logging.getLogger(__name__)

User = get_user_model()

INVITATION_EXPIRY_DAYS = 7


class InvitationError(Exception):
    """Base exception for invitation-related errors."""


class InvitationExpiredError(InvitationError):
    """Raised when a token is found but has already expired."""


class InvitationAlreadyAcceptedError(InvitationError):
    """Raised when trying to accept an already-accepted invitation."""


class InvitationNotFoundError(InvitationError):
    """Raised when no invitation matches the given token."""


class InvitationEmailError(InvitationError):
    """Raised when invitation email delivery fails."""


class CompanyService:
    """Company lifecycle helpers."""

    @staticmethod
    def unique_slug(name: str) -> str:
        base = slugify(name) or "company"
        slug = base
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    @staticmethod
    def parse_team_names(raw: str) -> list[str]:
        names: list[str] = []
        for part in raw.replace(",", "\n").split("\n"):
            name = part.strip()
            if name and name not in names:
                names.append(name)
        return names

    def create_teams(
        self,
        company: Company,
        team_names: list[str],
        *,
        manager: User | None = None,
    ) -> list[Team]:
        created: list[Team] = []
        for name in team_names:
            team, was_created = Team.objects.get_or_create(
                company=company,
                name=name,
                defaults={"manager": manager},
            )
            if was_created:
                created.append(team)
                logger.info("Team created: %s (company=%s)", team.pk, company.slug)
        return created

    def create_company(
        self,
        *,
        name: str,
        owner: User,
        max_users: int = 50,
        team_names: list[str] | None = None,
    ) -> Company:
        company = Company.objects.create(
            name=name,
            slug=self.unique_slug(name),
            owner=owner,
            max_users=max_users,
        )
        owner.company = company
        owner.save(update_fields=["company"])
        if team_names:
            self.create_teams(company, team_names, manager=owner)
        logger.info("Company created: %s (slug=%s, owner=%s)", company.pk, company.slug, owner.pk)
        return company


company_service = CompanyService()


class InvitationService:
    """
    Service layer for invitation lifecycle management.

    Usage:
        service = InvitationService()
        invitation = service.create_invitation(
            email='employee@example.com',
            company=company,
            invited_by=manager_user,
            role=Role.EMPLOYEE,       # optional
            team=team,                # optional
        )
        service.send_invitation(invitation, base_url='https://app.questflow.io')
    """

    # ------------------------------------------------------------------ #
    # Create                                                               #
    # ------------------------------------------------------------------ #

    def create_invitation(
        self,
        *,
        email: str,
        company: Company,
        invited_by: User,
        role: str = Role.EMPLOYEE,
        team: Team | None = None,
    ) -> Invitation:
        """
        Create (or re-send) an invitation for *email* to join *company*.

        If a non-accepted invitation for this email+company already exists,
        it is refreshed (token regenerated, expiry extended) rather than
        duplicated.
        """
        invitation, created = Invitation.objects.get_or_create(
            email=email,
            company=company,
            is_accepted=False,
            defaults={
                "invited_by": invited_by,
                "role": role,
                "team": team,
                "expires_at": timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS),
            },
        )

        if not created:
            # Refresh existing invitation so the recipient gets an up-to-date link
            import uuid
            invitation.invited_by = invited_by
            invitation.role = role
            invitation.team = team
            invitation.token = uuid.uuid4()
            invitation.expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
            invitation.save(update_fields=["invited_by", "role", "team", "token", "expires_at"])
            logger.info(
                "Refreshed invitation %s for %s → %s",
                invitation.pk, email, company.slug,
            )
        else:
            logger.info(
                "Created invitation %s for %s → %s",
                invitation.pk, email, company.slug,
            )

        return invitation

    def create_and_send_invitation(
        self,
        *,
        email: str,
        company: Company,
        invited_by: User,
        role: str = Role.EMPLOYEE,
        team: Team | None = None,
        base_url: str = "",
    ) -> Invitation:
        """
        Create (or refresh) an invitation and send the email immediately.
        """
        invitation = self.create_invitation(
            email=email,
            company=company,
            invited_by=invited_by,
            role=role,
            team=team,
        )
        invitation = self._get_invitation_for_email(invitation.pk)
        self.send_invitation(invitation, base_url=base_url)
        return invitation

    def _get_invitation_for_email(self, invitation_id: int) -> Invitation:
        return Invitation.objects.select_related(
            "company", "team", "invited_by"
        ).get(pk=invitation_id)

    def _get_from_email(self) -> str:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if not from_email:
            raise InvitationEmailError(
                _("DEFAULT_FROM_EMAIL is not configured.")
            )

        _display_name, from_addr = parseaddr(from_email)
        if not from_addr:
            raise InvitationEmailError(
                _("DEFAULT_FROM_EMAIL has invalid format. Use: Name <email@domain.com>")
            )

        if from_addr.lower().endswith(("@smtp-brevo.com", "@smtp-relay.brevo.com")):
            raise InvitationEmailError(
                _(
                    "DEFAULT_FROM_EMAIL must be a verified sender in Brevo "
                    "(your real email or domain), not the SMTP login *@smtp-brevo.com. "
                    "Add a sender under Brevo → Senders & IP, verify it, then update .env."
                )
            )

        return from_email

    # ------------------------------------------------------------------ #
    # Send e-mail                                                          #
    # ------------------------------------------------------------------ #

    def _build_invitation_email_context(
        self,
        invitation: Invitation,
        *,
        base_url: str = "",
    ) -> dict:
        if not base_url:
            base_url = getattr(settings, "SITE_URL", "").rstrip("/")

        accept_url = f"{base_url}/invite/{invitation.token}/"

        return {
            "invitation": invitation,
            "accept_url": accept_url,
            "company_name": invitation.company.name,
            "role_label": invitation.get_role_display(),
            "team_name": invitation.team.name if invitation.team else None,
            "invited_by_name": (
                invitation.invited_by.get_full_name()
                if invitation.invited_by
                else "QuestFlow"
            ),
            "expiry_days": INVITATION_EXPIRY_DAYS,
            "expires_at": invitation.expires_at,
        }

    def send_invitation(
        self,
        invitation: Invitation,
        *,
        base_url: str = "",
    ) -> None:
        """
        Render templates/emails/invitation.html and send to invitation.email.

        Raises InvitationEmailError when delivery fails.
        """
        if not invitation.email:
            raise InvitationEmailError(_("Invitation has no recipient email."))

        if invitation.pk:
            invitation = self._get_invitation_for_email(invitation.pk)

        subject = _("You're invited to join %(company)s on QuestFlow") % {
            "company": invitation.company.name,
        }

        try:
            context = self._build_invitation_email_context(
                invitation, base_url=base_url
            )
            html_body = render_to_string("emails/invitation.html", context)
            text_body = render_to_string("emails/invitation.txt", context)
        except Exception as exc:
            logger.exception(
                "Failed to render invitation email for invitation %s",
                invitation.pk,
            )
            raise InvitationEmailError(
                _("Could not prepare the invitation email.")
            ) from exc

        from_email = self._get_from_email()

        try:
            message = EmailMultiAlternatives(
                subject=str(subject),
                body=text_body,
                from_email=from_email,
                to=[invitation.email],
            )
            message.attach_alternative(html_body, "text/html")
            sent_count = message.send(fail_silently=False)
            if sent_count < 1:
                raise InvitationEmailError(
                    _("Email backend did not send the message.")
                )
        except InvitationEmailError:
            raise
        except smtplib.SMTPAuthenticationError as exc:
            logger.exception(
                "SMTP authentication failed for invitation %s",
                invitation.pk,
            )
            raise InvitationEmailError(
                _("SMTP authentication failed. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD.")
            ) from exc
        except smtplib.SMTPException as exc:
            logger.exception(
                "SMTP error sending invitation to %s (invitation %s)",
                invitation.email,
                invitation.pk,
            )
            raise InvitationEmailError(
                _("Could not deliver the invitation email: %(error)s") % {"error": exc}
            ) from exc
        except Exception as exc:
            logger.exception(
                "Failed to send invitation email to %s (invitation %s)",
                invitation.email,
                invitation.pk,
            )
            raise InvitationEmailError(
                _("Could not deliver the invitation email. Please try again.")
            ) from exc

        _display_name, from_addr = parseaddr(from_email)
        logger.info(
            "Invitation email accepted by SMTP: to=%s from=%s subject=%r invitation_id=%s",
            invitation.email,
            from_addr,
            str(subject),
            invitation.pk,
        )

    def send_invitation_email(
        self,
        invitation: Invitation,
        *,
        base_url: str = "",
    ) -> None:
        """Backward-compatible alias for :meth:`send_invitation`."""
        self.send_invitation(invitation, base_url=base_url)

    # ------------------------------------------------------------------ #
    # Accept                                                               #
    # ------------------------------------------------------------------ #

    def validate_invitation(self, token: str) -> Invitation:
        """
        Check if an invitation is valid without accepting it.
        """
        try:
            invitation = Invitation.objects.select_related(
                "company", "team"
            ).get(token=token)
        except Invitation.DoesNotExist:
            raise InvitationNotFoundError(
                f"No invitation found for token {token!r}."
            )

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError(
                f"Invitation {token!r} was already accepted."
            )

        if invitation.expires_at < timezone.now():
            raise InvitationExpiredError(
                f"Invitation {token!r} expired at {invitation.expires_at}."
            )

        return invitation

    def accept_invitation(self, token: str) -> Invitation:
        """
        Mark an invitation as accepted after verifying it is still valid.

        Returns the updated Invitation instance.
        Raises InvitationNotFoundError, InvitationExpiredError, or
        InvitationAlreadyAcceptedError on failure.
        """
        try:
            invitation = Invitation.objects.select_related(
                "company", "team"
            ).get(token=token)
        except Invitation.DoesNotExist:
            raise InvitationNotFoundError(
                f"No invitation found for token {token!r}."
            )

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError(
                f"Invitation {token!r} was already accepted."
            )

        if invitation.expires_at < timezone.now():
            raise InvitationExpiredError(
                f"Invitation {token!r} expired at {invitation.expires_at}."
            )

        invitation.is_accepted = True
        invitation.save(update_fields=["is_accepted"])

        logger.info(
            "Invitation %s accepted (company=%s, email=%s)",
            invitation.pk, invitation.company.slug, invitation.email,
        )

        return invitation

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def get_pending_invitations(self, company: Company):
        """Return all valid, unaccepted invitations for a company."""
        return Invitation.objects.filter(
            company=company,
            is_accepted=False,
            expires_at__gt=timezone.now(),
        ).select_related("team", "invited_by").order_by("-created_at")

    def revoke_invitation(self, invitation: Invitation) -> None:
        """
        Revoke an invitation by setting expiry to now.
        The token becomes invalid immediately.
        """
        invitation.expires_at = timezone.now()
        invitation.save(update_fields=["expires_at"])
        logger.info("Revoked invitation %s (%s)", invitation.pk, invitation.email)
