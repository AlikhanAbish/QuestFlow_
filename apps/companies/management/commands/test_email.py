"""
Send a test email using current Django email settings.

Usage:
    python manage.py test_email you@example.com
"""
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email via configured SMTP (Brevo) and print diagnostics."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Recipient email address")

    def handle(self, *args, **options):
        recipient = options["recipient"].strip()
        from_email = settings.DEFAULT_FROM_EMAIL
        _, from_addr = parseaddr(from_email)

        self.stdout.write(f"EMAIL_BACKEND = {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST    = {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        self.stdout.write(f"FROM          = {from_email}")
        self.stdout.write(f"FROM (parsed) = {from_addr or '(invalid)'}")
        self.stdout.write(f"TO            = {recipient}")

        if not from_addr:
            raise CommandError("DEFAULT_FROM_EMAIL is missing or invalid.")

        if from_addr.lower().endswith(("@smtp-brevo.com", "@smtp-relay.brevo.com")):
            raise CommandError(
                "DEFAULT_FROM_EMAIL must be a verified sender in Brevo "
                "(your real email or domain), NOT the SMTP login *@smtp-brevo.com. "
                "Brevo → Senders & IP → add and verify a sender, then update .env."
            )

        message = EmailMultiAlternatives(
            subject="QuestFlow test email",
            body="If you received this, SMTP delivery from QuestFlow works.",
            from_email=from_email,
            to=[recipient],
        )
        message.attach_alternative(
            "<p>If you received this, <strong>SMTP delivery</strong> from QuestFlow works.</p>",
            "text/html",
        )

        try:
            sent = message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f"SMTP send failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"SMTP accepted message (sent={sent})."))
        self.stdout.write(
            "If the inbox is empty: check Spam, wait a few minutes, then open "
            "Brevo → Transactional → Logs for delivery/bounce status."
        )
        self.stdout.write(
            "If FROM still shows *@smtp-brevo.com after editing .env: "
            "docker compose up -d --force-recreate django "
            "(restart does not reload env_file)."
        )
