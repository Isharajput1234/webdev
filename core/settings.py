import os
from pathlib import Path

from .env import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env (local secrets) if present.
# Supports both:
# - <repo>/django-job-portal-fullstack-main/.env
# - <repo>/.env (common in nested project layouts)
load_dotenv(BASE_DIR)
load_dotenv(BASE_DIR.parent)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
    if h.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Custom apps
    'apps.accounts.apps.AccountsConfig',
    'apps.jobs.apps.JobsConfig',
    'apps.dashboard.apps.DashboardConfig',
]
AUTH_USER_MODEL = 'accounts.CustomUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,
        },
    }
}

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'dashboard:employer_dashboard'
LOGOUT_REDIRECT_URL = 'jobs:home'

# Email (OTP)
# Set DJANGO_USE_CONSOLE_EMAIL=true to print OTP codes in the terminal (easiest for local dev).
# Otherwise configure SMTP in .env (see .env.example).
_EMAIL_DEBUG = os.getenv("DJANGO_EMAIL_DEBUG", "false").lower() == "true"
_EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
_EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "").strip().strip('"').strip("'")
_HAS_SMTP = bool(_EMAIL_HOST_USER and _EMAIL_HOST_PASSWORD)
_USE_CONSOLE_EMAIL = os.getenv("DJANGO_USE_CONSOLE_EMAIL", "false").lower() == "true"

if _USE_CONSOLE_EMAIL:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
elif os.getenv("DJANGO_EMAIL_BACKEND"):
    EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND")
elif os.getenv("DJANGO_EMAIL_HOST") and _HAS_SMTP:
    EMAIL_BACKEND = "core.email_backends.DebugSMTPEmailBackend" if _EMAIL_DEBUG else "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@jobportal.local").strip().strip('"').strip("'")
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = _EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = _EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.getenv("DJANGO_EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("DJANGO_EMAIL_TIMEOUT", "20"))

# AI features
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
AI_MATCH_THRESHOLD = float(os.getenv("AI_MATCH_THRESHOLD", "80"))
AI_DISPLAY_MIN_SCORE = float(os.getenv("AI_DISPLAY_MIN_SCORE", "10"))
# Career chat: auto | openai | gemini | rules
AI_CHAT_PROVIDER = os.getenv("AI_CHAT_PROVIDER", "auto")