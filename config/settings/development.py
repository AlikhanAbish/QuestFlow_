import os

from dotenv import load_dotenv

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['https://questflow.online' ,'localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

INTERNAL_IPS = ['127.0.0.1']

# Use PostgreSQL from base.py if DB_HOST is set, otherwise fallback to SQLite
if not os.getenv('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Prefer mounted .env over stale Docker env (restart does not reload env_file).
load_dotenv(BASE_DIR / '.env', override=True)

# Email backend: use console in development for easier testing
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
# Brevo API key (fallback for production)
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
# Sender email (used by BrevoEmailService)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')

