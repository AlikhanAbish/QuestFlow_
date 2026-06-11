import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'unsafe-fallback-key')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party apps
    'django_htmx',
    'django_celery_beat',
    'rest_framework',
    'axes',
    
    # Local apps (will be created later)
    'apps.core',
    'apps.accounts',
    'apps.companies',
    'apps.tasks',
    'apps.gamification',
    'apps.notifications',
    'apps.burnout',
    'apps.telegram_bot',
    'apps.admin_panel',
    # 'apps.analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # TZ 2.1.3 Пункт 3: award daily_login XP on first request per day
    'apps.gamification.middleware.DailyLoginXPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'apps.core.middleware.HtmxToastMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,           # важно для Railway
    )
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST', 'localhost'),
#         'PORT': os.getenv('DB_PORT', '5432'),
#     }
# }

AUTH_USER_MODEL = 'accounts.User'

# ---------------------------------------------------------------------------
# Email (Brevo API v3 — TZ 7.3)
# ---------------------------------------------------------------------------
SITE_URL = os.environ.get("SITE_URL", "https://questflow.online")

# Позволяет Django правильно определять хост и протокол (http/https) за прокси-сервером Railway
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Brevo API key for sending emails via HTTP (more reliable than SMTP on Railway)
BREVO_API_KEY = os.getenv('BREVO_API_KEY')

# Verified sender in Brevo (Senders & IP) — the "From" email address
# NOT the SMTP login *@smtp-brevo.com
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "invite@questflow.online")

# Email backend — for development/testing only
# BrevoEmailService detects console backend mode and uses it instead of Brevo API.
# Set EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend' in .env or settings/development.py
# for development (emails will be printed to console).
# In production, leave empty — BrevoEmailService will use Brevo HTTP API.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', '')

# ---------------------------------------------------------------------------
# Telegram Bot (TZ 6.2 / 7.3)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'QuestFlowBot')

# Redis & Celery Base Config
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_CREATE_MISSING_QUEUES = True
# Telegram bot tasks use queue="telegram"; worker must include: -Q celery,telegram

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL'),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

# django-axes: brute-force protection (TZ 6.2)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

import sys
if 'test' in sys.argv:
    AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    AXES_ENABLED = False

# ---------------------------------------------------------------------------
# Celery Beat Schedule  (TZ 6.6)
# ---------------------------------------------------------------------------
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # Reset streaks for users inactive > 1 day — daily at 00:05 UTC
    'check-streak-breaks': {
        'task': 'apps.gamification.tasks.check_streak_breaks',
        'schedule': crontab(hour=0, minute=5),
    },
    # Reset weekly_xp for all users — every Monday at 00:01 UTC
    'reset-weekly-xp': {
        'task': 'apps.gamification.tasks.reset_weekly_xp',
        'schedule': crontab(hour=0, minute=1, day_of_week=1),
    },
    # TZ 6.6: Telegram — daily morning reminder at 09:00 UTC
    'send-daily-reminders': {
        'task': 'apps.telegram_bot.tasks.send_daily_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    # TZ 6.6 / 2.1.4: Telegram — self-assessment reminder on Fridays at 17:00 UTC
    'send-assessment-reminders': {
        'task': 'apps.telegram_bot.tasks.send_assessment_reminders',
        'schedule': crontab(hour=17, minute=0, day_of_week=5),
    },
    # TZ 6.6: Clean up old read notifications weekly on Sunday at 02:00 UTC
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
}
