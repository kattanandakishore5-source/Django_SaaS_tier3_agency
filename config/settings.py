import os
import sys
from pathlib import Path
from decouple import config, Csv

# Testing flag for runtime behavior adjustments in unit tests
TESTING = any('test' in str(a) for a in sys.argv)

# Patch for template Context copy compatibility in some Python/Django combos.
try:
    from copy import copy as _copy
    from django.template import context as _django_template_context

    def _basecontext_copy(self):
        # Create a new empty instance and copy the dicts list
        duplicate = object.__new__(self.__class__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    def _context_copy(self):
        duplicate = _basecontext_copy(self)
        # copy render_context if present
        if hasattr(self, 'render_context'):
            duplicate.render_context = _copy(self.render_context)
        return duplicate

    _django_template_context.BaseContext.__copy__ = _basecontext_copy
    _django_template_context.Context.__copy__ = _context_copy
except Exception:
    # If patching fails, continue without breaking settings import.
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'django_extensions',
    # 'drf_yasg' intentionally conditionally loaded below to avoid import-time issues in test environments

    'django_htmx',
    # Local apps
    'apps.accounts',
    'apps.dashboard',
    'apps.core',
    'apps.tenancy',
    'apps.audit',
    'apps.billing',
]

# Conditionally enable drf_yasg only if the package is importable (prevents pkg_resources import errors in minimal test envs)
try:
    import drf_yasg  # type: ignore
    INSTALLED_APPS.append('drf_yasg')
except Exception:
    # drf_yasg not available in this environment (ok for unit tests)
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenancy.middleware.WorkspaceContextMiddleware',
    'apps.accounts.middleware.Pending2FAMiddleware',
    'apps.audit.middleware.AuditLoggingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

DB_HOST_VAL = config('DB_HOST', default='')
DB_ENGINE_VAL = config('DB_ENGINE', default='django.db.backends.postgresql' if DB_HOST_VAL else 'django.db.backends.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE_VAL,
        'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3') if 'sqlite' in DB_ENGINE_VAL else 'django_admin_pro'),
        'USER': config('DB_USER', default='admin'),
        'PASSWORD': config('DB_PASSWORD', default='admin123'),
        'HOST': DB_HOST_VAL if DB_HOST_VAL else 'localhost',
        'PORT': config('DB_PORT', default='5432'),
    }
}


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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.CustomUser'

# Custom User Model
CUSTOM_USER_EMAIL_FIELD = 'email'
CUSTOM_USER_USERNAME_FIELD = 'email'

# Authentication Redirects
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    }
}

# CORS_ALLOWED_ORIGINS defined securely below with CSRF_TRUSTED_ORIGINS

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Celery / Broker configuration
# Pull from environment with safe defaults for local development.
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
# Use JSON-only serialization for safety
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
# Align Celery timezone with Django
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Security
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Proxy HTTPS headers
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS & CSRF
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173', cast=Csv())

# Pagination
DEFAULT_PAGE_SIZE = 20

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Environment Validation for Production
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured
    if SECRET_KEY == 'django-insecure-change-this-in-production':
        raise ImproperlyConfigured("SECRET_KEY must be configured in production.")
    if DATABASES['default']['PASSWORD'] == 'admin123':
        raise ImproperlyConfigured("DB_PASSWORD must be configured in production.")

# Stripe & Billing Configuration
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='pk_test_mock')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_mock')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='whsec_mock')
STRIPE_PRICE_BASIC = config('STRIPE_PRICE_BASIC', default='price_basic_test')
STRIPE_PRICE_PRO = config('STRIPE_PRICE_PRO', default='price_pro_test')

# Magic Link Configuration
MAGIC_LINK_EXPIRY_MINUTES = config('MAGIC_LINK_EXPIRY_MINUTES', default=15, cast=int)




