from email.utils import parseaddr

from django.conf import settings
from django.core.checks import Error, Warning, register


def _from_address() -> str:
    _, addr = parseaddr(getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '')
    return (addr or '').lower()


@register()
def check_email_configuration(app_configs, **kwargs):
    errors = []
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if 'smtp' not in backend:
        return errors

    if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
        errors.append(
            Warning(
                'EMAIL_HOST_PASSWORD is empty; SMTP email will fail.',
                id='companies.W001',
            )
        )

    from_addr = _from_address()
    if not from_addr:
        errors.append(
            Error(
                'DEFAULT_FROM_EMAIL is not set. Use a verified Brevo sender, e.g. '
                '"QuestFlow <you@gmail.com>" (quotes required in .env if the value contains spaces).',
                id='companies.E001',
            )
        )
    elif from_addr.endswith(('@smtp-brevo.com', '@smtp-relay.brevo.com')):
        errors.append(
            Error(
                'DEFAULT_FROM_EMAIL must be a verified sender in Brevo, not the SMTP login '
                '*@smtp-brevo.com. Add a sender under Brevo → Senders & IP.',
                id='companies.E002',
            )
        )

    return errors
