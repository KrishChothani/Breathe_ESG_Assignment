"""
Production Settings
===================
Reads all secrets from environment variables. PostgreSQL via DATABASE_URL.
Static files served via WhiteNoise. Never commit real values here.
DATABASE_URL and other config is inherited from base.py.
"""

import os
from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Hard fail if not set

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# ── DATABASES comes from base.py (dj_database_url.config via DATABASE_URL) ───
# Do NOT override DATABASES here.

# ── Static files via WhiteNoise ───────────────────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Security Headers ──────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Navan API ─────────────────────────────────────────────────────────────────
NAVAN_CLIENT_ID     = os.environ.get('NAVAN_CLIENT_ID', '')
NAVAN_CLIENT_SECRET = os.environ.get('NAVAN_CLIENT_SECRET', '')
NAVAN_AUTH_URL      = os.environ.get('NAVAN_AUTH_URL', 'https://api.navan.com/auth/v1/token')
NAVAN_BASE_URL      = os.environ.get('NAVAN_BASE_URL', 'https://app.navan.com/open-api/trips/v1')

# ── Concur API ────────────────────────────────────────────────────────────────
CONCUR_CLIENT_ID     = os.environ.get('CONCUR_CLIENT_ID', '')
CONCUR_CLIENT_SECRET = os.environ.get('CONCUR_CLIENT_SECRET', '')
CONCUR_BASE_URL      = os.environ.get('CONCUR_BASE_URL', 'https://us.api.concursolutions.com')
