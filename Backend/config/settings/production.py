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

# ── ALLOWED_HOSTS — hard-coded to include all deployment targets ──────────────
ALLOWED_HOSTS = [
    # Local
    'localhost', '127.0.0.1', '0.0.0.0',
    # EC2 public IP — update if your EC2 IP changes
    '13.233.233.129',
    # ngrok tunnels — wildcard subdomains
    '.ngrok-free.app',
    '.ngrok.io',
    # Vercel frontend + preview URLs
    'cks-breatheesg.vercel.app',
    'breatheesg.vercel.app',
    '.vercel.app',
    # If ALLOWED_HOSTS env var set to '*', honour it
    *([os.environ.get('ALLOWED_HOSTS', '')] if os.environ.get('ALLOWED_HOSTS', '').strip() == '*' else []),
]

# ── DATABASES comes from base.py (dj_database_url.config via DATABASE_URL) ───
# Do NOT override DATABASES here.

# ── Static files via WhiteNoise ───────────────────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Security Headers ──────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0          # Disabled — using ngrok/HTTP in this deployment
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False    # Set True only when on real HTTPS with fixed domain
CSRF_COOKIE_SECURE = False
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
