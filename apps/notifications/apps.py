from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"
    
    def ready(self):
        """Validate email configuration on app startup."""
        # Only validate in production (DEBUG=False)
        if not settings.DEBUG:
            self._validate_email_config()
    
    @staticmethod
    def _validate_email_config():
        """Check that Brevo API is properly configured for production."""
        brevo_api_key = getattr(settings, 'BREVO_API_KEY', '')
        default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        
        # Check if using console backend (development mode)
        if 'console' in email_backend.lower():
            logger.warning(
                "Using console email backend in production. "
                "Emails will not be delivered. This is only for development."
            )
            return
        
        # Check Brevo API key
        if not brevo_api_key:
            logger.error(
                "BREVO_API_KEY is not configured. "
                "Set it in .env: https://app.brevo.com/settings/account/api"
            )
            raise RuntimeError(
                "BREVO_API_KEY is required for email delivery in production. "
                "Configure it in .env and restart the application."
            )
        
        # Check DEFAULT_FROM_EMAIL
        if not default_from_email:
            logger.error("DEFAULT_FROM_EMAIL is not configured in settings.")
            raise RuntimeError(
                "DEFAULT_FROM_EMAIL is required for email delivery. "
                "Configure it in .env and restart the application."
            )
        
        # Warn if using SMTP login instead of verified sender
        if '@smtp' in default_from_email.lower():
            logger.error(
                "DEFAULT_FROM_EMAIL looks like an SMTP login (@smtp-brevo.com). "
                "It should be a verified sender email (your actual domain). "
                "Go to https://app.brevo.com/settings/senders-ip to verify a sender."
            )
            raise RuntimeError(
                "DEFAULT_FROM_EMAIL must be a verified Brevo sender, not an SMTP login. "
                "Update it in .env and restart the application."
            )
        
        logger.info(
            "Email configuration valid: using Brevo API for outgoing email (from=%s)",
            default_from_email,
        )
