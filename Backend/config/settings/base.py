"""
BreatheESG Base Settings
========================
Shared across all environments. Do NOT put environment-specific values here.
Use development.py or production.py overlays for those.
"""

import os
import dj_database_url
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load .env from Backend/ directory
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
# Must be set via DJANGO_SECRET_KEY environment variable in all real environments
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'fallback-insecure-key-only-for-local-do-not-use-in-prod'
)

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ── Database — Supabase PostgreSQL ────────────────────────────────────────────
# Always driven by DATABASE_URL environment variable.
# No SQLite fallback — forces the correct behaviour in every environment.
_db_config = dj_database_url.config(
    default=os.environ.get('DATABASE_URL'),
    conn_max_age=600,
    conn_health_checks=True,
    ssl_require=True,
)
# Add keepalive + timeout options to survive Supabase pooler idle timeouts
_db_config.setdefault('OPTIONS', {}).update({
    'connect_timeout': 30,
    'keepalives': 1,
    'keepalives_idle': 60,
    'keepalives_interval': 10,
    'keepalives_count': 5,
})
DATABASES = {'default': _db_config}

# ── Application Definition ────────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
]

LOCAL_APPS = [
    'core',
    'apps.users',
    'apps.organisations',
    'apps.ingestion',
    'apps.emissions',
    'apps.review',
    'apps.reports',
    'apps.chatbot',            # LangGraph Text-to-SQL chatbot
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'users.User'

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.TenantMiddleware',   # attaches active_organisation + active_role from JWT
]

ROOT_URLCONF = 'config.urls'

# ── Templates ─────────────────────────────────────────────────────────────────
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

# ── Password Validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── File Upload ───────────────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB

# ── CORS — hard-coded open (update when moving to dedicated server) ───────────
CORS_ALLOW_ALL_ORIGINS   = True     # Accept requests from ANY origin (*)
CORS_ALLOW_CREDENTIALS   = True
CORS_ALLOW_ALL_HEADERS   = True     # Accept ALL request headers

# Explicit list as backup — ensures ngrok-skip-browser-warning is always allowed
CORS_ALLOW_HEADERS = list([
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'ngrok-skip-browser-warning',   # ← required for ngrok tunnels
    'cache-control',
    'pragma',
])

CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

# Hard-coded trusted origins (belt-and-suspenders alongside CORS_ALLOW_ALL_ORIGINS)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:3000',
    'https://cks-breatheesg.vercel.app',    # ← production frontend
    'https://breatheesg.vercel.app',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[a-z0-9-]+\.ngrok-free\.app$',   # any ngrok-free URL
    r'^https://[a-z0-9-]+\.ngrok\.io$',
    r'^https://[a-zA-Z0-9-]+\.vercel\.app$',    # any vercel preview URL
]

# ── Chatbot / LangGraph ────────────────────────────────────────────────────────
# GEMINI_API_KEY must be set in your .env file.
# CHATBOT_MODEL defaults to gemini-1.5-pro (Gemini).
GEMINI_API_KEY     = os.environ.get('GEMINI_API_KEY', '')
CHATBOT_MODEL      = os.environ.get('CHATBOT_MODEL', 'gemini-2.0-flash')
CHATBOT_MAX_TOKENS = int(os.environ.get('CHATBOT_MAX_TOKENS', '1000'))
CHATBOT_RATE_LIMIT = int(os.environ.get('CHATBOT_RATE_LIMIT', '30'))  # per user per hour

# ── Cache (conversation memory + rate limiting) ───────────────────────────────
# If REDIS_URL is set, use Redis. Otherwise fall back to in-process LocMemCache.
_REDIS_URL = os.environ.get('REDIS_URL', '')
if _REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'breathe-esg-chatbot',
        }
    }